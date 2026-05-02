#APIs & project IDs, settings 

#Big query doesn't need APIs to be accessed, instead auth can be used along with service account 
# service account : when i open the BigQuery i log in right away my identity was defined already, when using authentication from python code, BigQuery doesn't know the identity 
#so account service creates a json file that would define the authentication identity it's like a permission for access

API_KEY = "https://api.mockbank.com/v1/notifications"
API_URL_KEY = "sk_123456789abcdef"
API_PATH_NOTIFS = "/Users/user/Downloads/Notifications - Notifications.csv"
API_PATH_USERS = "/Users/user/Downloads//users" 
API_PATH_TRANSACTIONS = "/Users/user/Downloads/Transaction.csv"
PROJECT_BIGQUERY_ID = "callcenter"
PROJECT_DATASET_NAME = "neo.notifications"
MCC_PATH = "/Users/user/Downloads/mcc_codes.csv"




# METAL_RESERVE_PLAN : User is interested in upgrading / premium plan / high value
# REENGAGEMENT_ACTIVE_FUNDS : User has money but is not active
# PREMIUM_ENGAGEMENT_FEES_SAVED : Showing user how much money they saved
# PREMIUM_ENGAGEMENT_INACTIVE_CARD : Premium user but not using card


# PUMPKIN_PAYMENT_NOTIFICATION : A payment happened (seasonal or campaign)
# ENGAGEMENT_SPLIT_BILL_RESTAURANT : User paid at restaurant → suggest split bill
# MADE_MONEY_REQUEST_NOT_SPLIT_BILL : User requested money but didn’t use split feature


# NO_INITIAL_CARD_ORDER : Signed up but didn’t order card
# NO_INITIAL_CARD_USE : Has card but never used it
# NO_INITIAL_FREE_PROMOPAGE_CARD_ORDER : Saw promo but didn’t order card : failed ads inside our platform
# ONBOARDING_TIPS_ACTIVATED_USERS : Help new users understand features


# FIFTH_PAYMENT_PROMO : Reward after 5 payments
# WELCOME_HOME : Welcome / reactivation message
# METAL_GAME_START : Gamified campaign


# LOST_CARD_ORDER : User reported lost card / ordered new one




#for value in values : 

# this loop iterate over each row, col, cell it depends on "values"

#if values is dataframe "for values in dataframe :" then it'll iterate over each col (horizontal)
#if values is col "for vaues in dataframe['col'] :" then i'll iterate over each cell  
#if values should be rows "for values in dataframe.iterrows()" 

#If you want index + value (like iterrows but for a column)

#for index, value in df['age'].items():


# now basically  