import pandas as pd 
import csv 
import numpy as np
from fetch_data_csv import FetchPull_notifs
from preprocess_data import preprocess_data
from churn import create_churn_labels, classification_report, confusion_matrix, model_creation


def main():
    print("Pipeline started")
    #fetch_data -- first file
    notifs = FetchPull_notifs()
    print("notifications_data_fetched")

    trans = pd.DataFrame()
    users = pd.DataFrame()
    mcc = pd.DataFrame()

    #preprocess -- second file

    full_data, candidates = preprocess_data(notifs, trans, users, mcc)
    print(f'data has been processed, full data available : {full_data}')
    print(f'Notifications organized notifs to be sent : {candidates}')

    #churn -- third file
    
    churn_labels = create_churn_labels(full_data)
    training_df = pd.merge(full_data, churn_labels, on='user_id')

    #model

    model, report, matrix = model_creation(training_df=training_df)

    print(report)
    print(matrix)

    if __name__ == "__main__":
        main()
        print("🚀 Pipeline started")
