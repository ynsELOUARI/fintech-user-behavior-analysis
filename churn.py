import pandas as pd
import numpy as np 
import config
from preprocess_data import preprocess_data
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix
from datetime import datetime, timedelta
import matplotlib.pyplot as plt



def create_churn_labels(df, churn_window_limitations=365):

    #classify churn 
    #turn sent at to datetime and transaction dates as well as we are checking if that person made a transaction in last 356 days
    df['sent_at'] = pd.to_datetime(df['Notifications_date'])
    df['transactions_date'] = pd.to_datetime(df['transactions_date'])

    #now we will loop through each row before setting the condition

    labels = []
    #we will loop through each and every row to check if users are churned 
    #we'll use group so we can use group by inside the for loop
    for uid, group in df.groupby('user_id'):

        transactions = group['transactions_date'].sort_values()

        # after we set the the deadline we will set the condition of the future_txn that needs to be checked if they are churned or not 
        # first : transaction should be after the notification sent 
        # second : transaction should be smaller than churn_window_limitations (365days) 
        for _, row in group.iterrows():
            sent_at = row['sent_at']
            dead_line = sent_at + timedelta(days=churn_window_limitations)
            future_txn = transactions[(transactions >= sent_at) & (transactions <= dead_line)]
            #churn :
            churned = 0 if len(future_txn) > 0 else 1

        #append here means we are filling the list with our details 
            labels.append({
                'user_id': uid,
                'transactions_date' : transactions,
                'churned' : churned
            })
    return pd.DataFrame(labels)   

# we will first name a df called training_df and then will merge both the 'List and 'full_data'
def model_creation(training_df):

    categorical_cols = ['plan', 'reason', 'channel']
    numeric_cols = ['is_new_user', 'has_card', 'high_amount']
    #turn text to col for ML preparation
    encoded_data = pd.get_dummies(training_df, columns=categorical_cols, drop_first=True)
    target = 'churned'
    #we have removed churned because it's like handing the model to cheat 
    #okey so it'll look at all the cols i have created with the conditions and cooldowns and then based on all those cols it'll lead to either 0 or 1 and so that's the purpose of training the model rather than giving it the answer in the first place which will not learn anything 
    dropped_col = ['transactions_date', 'sent_at', 'user_od', 'churned']
    feature = [col for col in encoded_data.columns if col not in dropped_col]

    #ML coordinates

    X = encoded_data[feature].fillna(0)
    y = encoded_data[target]

    X_train, X_test, y_train, y_test = train_test_split(X, y, random_state=42, test_size=0.2)
    
    #model selection 
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)    

    #n_estimators : means 50 tree will vote all together o yes or no for an output
    #okey for a single output all the trees asnwers or vote by yes or no, it comes from conditions inside each tree 
    
    report = classification_report(y_pred=y_test)
    matrix = confusion_matrix(y_test, y_pred)
    return model, report, matrix


    