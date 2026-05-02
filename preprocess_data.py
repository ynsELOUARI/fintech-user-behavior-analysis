import pandas as pd
import numpy as np 
import requests
import csv
import config
import logging
import json
from typing import Dict, List, Callable, Optional
from sqlalchemy import create_engine
from datetime import datetime, timedelta

# logging is a alert tells if one of the pipeline steps drops an error or failed 
# we start with this logging that we created one time, which gives us the error type and the time of all upcoming errors 
logging.basicConfig(level=logging.INFO, format="%(asctime)s -- %(levelname)s -- %(message)s")

def fetch_notifications():
    #pulled data already, now we'll access datasets to start data manipulation
    headers = {'Authorization' : f'Bearer {config.API_KEY}'}
    #pull notif data 
    response = requests.get(config.API_URL_NOTIFS, headers=headers)
    #this checks if the API response fails, it tells please 
    response.raise_for_status()
    return pd.DataFrame(response.json())

#pull transaction dataset

def fetch_transaction():
    headers = {'Authorization' : f'Bearer {config.API_KEY}'}
    response = requests.get(config.API_URL_TRANSACTIONS, headers=headers)
    response.raise_for_status()
    return pd.DataFrame(response.json())

def fetch_users():
    headers = {'Authorization' : f'Bearer {config.API_KEY}'}
    response = requests.get(config.API_URL_USERS, headers=headers)
    response.raise_for_status()
    return pd.DataFrame(response.json())

# start data manupilation
def preprocess_data(notifs_data, trans_data, users_data, mcc_data):
    logging.info("Starting preprocessing pipeline...")

    if hasattr(config, 'MCC_PATH'):
        mcc_data = pd.read_csv(config.MCC_PATH).rename(columns={'mcc' : 'ea_merchant_mcc'})    

    #merge data, with two conditions existence of the table and the existence of the primary key
    if not mcc_data.empty and 'ea_merchant_mcc' in trans_data.columns:
        trans_mcc = pd.merge(trans_data, mcc_data, on='ea_merchant_mcc', how='left')

    notif_trans = pd.merge(
        notifs_data,
        trans_mcc,
        on='user_id',
        how='left'
    )
    full_data = pd.merge(
        notif_trans,
        users_data,
        on='user_id'
    )
    full_data.drop(columns=['ea_merchant_city', 'ea_merchant_country', 
                            'num_referrals', 'num_successful_referrals',
                            'edited_description', 'irs_description',
                            'irs_reportable', 'usda_description',
                            'combined_description'], inplace=True)

    full_data.rename(columns=
                     {'created_date_x' : 'Notifications_date',
                      'created_date_y' : 'Transaction_date',
                      'created_date' : 'subscription_date'},
                      inplace=True
    )
    dates_cols = [
        'Notifications_date', 'Transaction_date', 'subscription_date'
    ]
    full_data[dates_cols] = full_data[dates_cols].apply(
        lambda x: pd.to_datetime(x, errors='coerce')   
    )

    # now we should clean data and filter 
    logging.info(f'Data fetched/merged: {full_data}')

    # we should start by creating the important boolean values :
    #  is_active, physical_card, users_received_ads, losing card, 

    # DEFINE FLAGS RELATIVE TO THEIR JOURNEY
    # Active = made at least one payment within X days of subscribing
    def compute_userbooleans(df, active_window_days=30):
        """ Adds true or false for each new created col to be prepared for rules"""
        full_data['subscription_date'] = pd.to_datetime(full_data['subscription_date'])
        full_data['last_txn_date'] = pd.to_datetime(full_data['last_txn_date'])
        
        full_data['days_since_signup'] = full_data['last_txn_date'] - full_data['subscription_date']
        full_data['is_active'] = full_data['last_txn_date'] <= active_window_days
        full_data['is_new_user'] = full_data['days_since_signup'] <= active_window_days

        # we will rely on a list of reasons that shows a card exists :
        CARD_PROOF_REASONS = [
            "LOST_CARD_ORDER", "NO_INITIAL_CARD_USE", "PREMIUM_ENGAGEMENT_INACTIVE_CARD"
            "FIFTH_PAYMENT_PROMO", "PUMPKIN_PAYMENT_NOTIFICATION", "ENGAGEMENT_SPLIT_BILL_RESTAURANT"
        ]
        
        full_data['has_card'] = full_data.groupby('user_id')['reason'].transform(
            lambda r : r.isin(CARD_PROOF_REASONS).any()
        )
        full_data['ordered_used_card'] =  full_data[full_data['reason']== 'NO_INITIAL_CARD_ORDER']
        full_data['has_prumiam_plan'] = full_data['plan'].isin(['PREMIUM', 'METAL'])
        full_data['has_prumiam_savings'] = full_data['reason'].isin('PREMIUM_ENGAGEMENT_FEES_SAVED')
        full_data['is_premium_candidate'] = (full_data['transactions_state']) == ('COMPLETED' & full_data['has_card'])
        full_data['LOST_CARD'] = full_data[full_data['reason'] == 'LOST_CARD_ORDER']



        full_data['high_amounts'] = full_data.groupby('user_id')['amount_usd'].transform('mean') > 150
        #create a list of MCC that are related to restaurants so we can track the 5th times restaurant payment
        RESTAURANT_MCC = [5811, 5812, 5813, 5814, 5815, 5816, 5817, 5818, 5819, 5820, 7800, 7832, 7841]
        #the condition : the MCCs should include the LIST WE CREATED 
        full_data['is_restaurant'] = full_data['ea_merchant_mcc'].isin(RESTAURANT_MCC)
        full_data['restaurant_payment_count'] = full_data.groupby('user_id')['is_restaurant'].transform('count')

        full_data['is_5th_restaurant_payment'] = (full_data['restaurant_payment_count'] >= 5) & \
                                                 (full_data['restaurant_payment_count'] % 5 == 0) 


        full_data['consent_marketing_email'] = full_data.get('attributes_notifications_marketing_email', False).astype('bool')
        full_data['consent_marketing_push'] = full_data.get('attributes_notifications_marketing_push', False).astype('bool')
        # this call includes at least of those channels was accepted 
        full_data['consent_any_marketing'] = full_data['consent_marketing_email'] | full_data['consent_marketing_push']
        return full_data
    
    
    
    Notifications_rules: Dict[str, dict] = {
        # we have created a dictionary but with a unique format "Dict[str, dict]" 
        # it means Dict : Notifications_rules, str : reason, dict : Dict settings



        #dictionary to create the steps of notifs
        #key is the reason : value is conditions, cooldowns..
        "NO_INITIAL_CARD_ORDER" : {
            #condition : here condition represents the filter of all the users by keeping only the ones haven't ordered the card 
            # which then we will specify the channel needed for the notifications that needs t be sent and the cooldown and timing of that 
            "Conditions" : lambda u: not u.get("has_card", False) and u.get("is_new_user", False),
            "channel" : ["EMAIL", "PUSH"],
            "consent" : "transactional", 
            "cooldown_days" : 7,
            "priority" : "high",
            #is urgent is used as an indicator of our data 
            "is_urgent" : False
        },

        #users who hasn't used the card while ordered it 
        "NO_INITIAL_CARD_USE" : {
            # we need to bnuild the condition first
            "Conditions" : lambda u : u.get("ordered_used_card", False),
            "channel" : ['EMAIL', 'PUSH'],
            "cooldown_days" : 15,
            "consent" : "marketing",
            "priority" : "medium",
            "is_urgent" : False
        },

        "LOST_CARD_ORDER" : {
            "Conditions" : lambda u : u.get('LOST_CARD', False),
            "channel" : ['EMAIL', 'PUSH', 'SMS'],
            "consent" : "transactional", 
            "cooldown_days" : 0,
            "priority" : "critical",
            "is_urgent" : True
        },
        
        "ONBOARDING_TIPS_ACTIVATED_USERS" : {
            "Conditions" : lambda u : u.get(full_data[full_data['reason'] == "ONBOARDING_TIPS_ACTIVATED_USERS"], False) and u.get(full_data['subscription_date']),
            "channel" : ['EMAIL', 'PUSH'],
            "consent" : "marketing",
            "cooldown_days" : 365,
            "priority" : "low",
            "is_urgent" : False
        },  

        # send the notif every 5th for each rich user
        "ENGAGEMENT_SPLIT_BILL_RESTAURANT" : {
            "Condition" : lambda u : u.get("high_amounts", False) and u.get("is_5th_restaurant_payment", False),
            "channel" : ['PUSH', 'EMAIL'],
            "consent" : "marketing",
            #cooldown isn't important
            "cooldown_days" : 7,
            "priority" : "medium",
            "is_urgent" : False
        },
    }

    #now basically we will start the 
    candidates = []

    #checks each row horizontally
    for _, user_row in full_data.iterrows():
        # user_dict is user row series gets converted to dict for better access
        user_dict = user_row.to_dict()
        #we check every key of dictionary
        for reason in Notifications_rules.keys():
            #we store them in "rule", now we have the keys and values we will organize sendings 
            rule = Notifications_rules[reason]
            # "not" is responsible of the skipping, so if we want to use a condition to skip "not" is the tool
            if not rule['Conditions'](user_dict): 
                continue
            # false used to avoid crashing our code if "is_urgent" isn't true in our dictionary
            if rule.get('is_urgent', False):
                send = True
            #if it's not urgent then follow "else" 
            else:
                #check if it's marketing or transactional, if transactional then it'll be sent

                consent_type = rule.get("consent", "marketing")
                if consent_type == "marketing":
                    channel = rule["channel"][0].upper()
                    consents = f"respect_user_consent"
                    # should send related to whether that user accepted those less important notifs or not
                    # if yes then please send yes send notifs, if no then do not send which let's respect their refusal of those notifs 
                    should_send = user_dict.get("consent", False)

                else:
                    #if it's not marketing then it's transational and it should be sent regardless bc it's important
                    should_send = True

                if should_send:
                    candidates.append({
                        "user_id": user_dict["user_id"],
                        "reason": reason,
                        "channel": channel,
                        "priority": rule.get("priority", "medium"),
                        "generated_at": datetime.now()
                })
                    logging.info(f'Generated {len(candidates)} notifications allowance')
                    return full_data, candidates

                

# we will add another thing important as well : 

        #here we tell python : do not run the code until ii execute it directly on the file
        # because when import this file in another file, it'll not be executed 
        # because if it's executed it will slow down my code and may be the whole operation or even my laptop 
    
if __name__ == "__main__":
    notifs = fetch_notifications()
    trans = fetch_transaction()
    users = fetch_users()
    mcc = pd.DataFrame()

    # basically we have already we have filtered data with two things. : 
    # candidates -- users that we should send notifications to. 
    # enriched -- full data with the preprocess funtion manupilation
    
    candidates, enriched = preprocess_data(notifs, trans, users, mcc)
    print(f"📤 To send: {len(candidates)}")
    if candidates:
        print("Example:", candidates[0])
logging.info(f'Generated {len(candidates)} notifications allowance')


    #we want to the determine the urgency of whether we should send the notif or not : the criteria would be :

    # it would depend on a very important strcutre which will be one of the two lists of cols we have 

    #classify : 
        #critical = ["LOST_CARD_ORDER", "NO_INITIAL_CARD_USE", "NO_INITIAL_CARD_ORDER","ONBOARDING_TIPS_ACTIVATED_USERS"(one time), "ENGAGEMENT_SPLIT_BILL_RESTAURANT"(for those rich ppl based on their usd amount, but send the notification only in every 5 payments at restaurant, and so you have the mcc that can tell you whether that person already paid in a restaurant), "FIFTH_PAYMENT_PROMO"(but we need to modify it to TENTH_PAYMENT_PROMO just to not keep sending them many notifications every 5 times it may not be good idea even if it's reward, so let's keep it tenth),""]

    

    