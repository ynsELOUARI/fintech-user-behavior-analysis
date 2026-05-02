import pandas as pd
import numpy as np 
import csv
import requests
import config
import main


#
def FetchPull_notifs():
    # We use dictionary headers, and Bearer – This tells the server that the request is using token-based authentication. It’s a standard keyword for “I’m sending a token you can trust.”
    #TOKEN is used along with the API as a secret key that proves you’re authorized to access that API
    headers = {'Authorization' : f'Bearer {config.API_KEY}'}
    #so basically we claim that we are asking for permission with the token of the API key
    #requests.get() needs a destination — where to send the request
    response = requests.get(config.API_URL_KEY, headers=headers)
    # response : we're requesting to pull data with the header dectionary that contains the API KEY and TOKEN

    if response.status_code != 200:
        raise Exception(f"API Error: {response.status_code}")
    
    #convert data into json 
    data = response.json()

    #dataframe creation
    df_error = pd.DataFrame(data)
    return df_error

if __name__ == "__main__":
    df = FetchPull_notifs()
    df.head()
    main()
