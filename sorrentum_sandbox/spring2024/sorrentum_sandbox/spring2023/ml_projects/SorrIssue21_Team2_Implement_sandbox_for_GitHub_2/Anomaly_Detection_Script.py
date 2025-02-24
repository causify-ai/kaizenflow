#!/usr/bin/env python3
# -*- coding: utf-8 -*-



#Installing the dask package
#!pip install dask

#Pulling required packages--
import pandas as pd
import math
import numpy as np 
import warnings
import dask.dataframe as dd
import dask.array as da
import dask.bag as db
import psycopg2 as psycop

warnings.filterwarnings("ignore")
pd.set_option('display.max_rows', None)

import sorrentum_sandbox.common.download as ssandown

#_LOG = logging.getLogger(__name__)

def get_db_connection(query_var) :       
   connection = psycop.connect(
          host="host.docker.internal",                                      
          dbname="airflow",
          port=5532,
          user="postgres",
          password="postgres")
   drt_cursor=connection.cursor()
   drt_cursor.execute(query_var)
   data=drt_cursor.fetchall()
   connection.close()
   return pd.DataFrame(data)


def downloader(pair,target_table,**kwargs):
    
    final_data=pd.DataFrame()
    #Pulling Data from Issues Table-
    issues_df = pd.read_csv('github_issues.csv') 
    issues_df=issues_df.drop(['closed_at'], axis=1)
    print("Pulling The Issues df:",issues_df.shape)


    #Pulling Data from Commits Table-
    commits_df = pd.read_csv('github_commits.csv')  
    print("Pulling the Commits df:",commits_df.shape)


    #Pulling Data from Main Table-
    main_df = pd.read_csv('github_main.csv')
    main_df = main_df.rename(columns = {'Crypto': 'Crypto_Name'}, inplace = False)
    print("Pulling the Main df:",main_df.shape)



    #Creating a list so that each datatable is analyised
    df_list=['issues_df','commits_df','main_df']
    for m in df_list :

        if m=='issues_df':
            ddf = dd.from_pandas(issues_df, npartitions=10) 

        elif m=='commits_df':
            ddf = dd.from_pandas(commits_df, npartitions=10) 
            
        elif m=='main_df':
            ddf = dd.from_pandas(main_df, npartitions=10) 
            

        if pair =='BTC':
            data=ddf[ddf['Crypto_Name']=='bitcoin']
        elif pair == 'SOL':
            data=ddf[ddf['Crypto_Name']=='solana']            
            
        print("Analysis for",m,'& Coin:',pair)
        print(data)


        #Code for Univariate analysis---
        #### code for catagorical data
        data_file = data.select_dtypes(exclude =np.number)
        def count_stats(column_data):
            total_count = column_data.count().compute()
            unique_count = column_data.nunique().compute()
            null_count = column_data.isnull().sum().compute()


            ## printing column counts
            #print('Total number of values : {}'.format(total_count))
            #print('Total number of unique values : {}'.format(unique_count))
            #print('Total number of null values : {}'.format(null_count))

            return total_count, unique_count, null_count

        discrete_dataFrame_columns = ['Column_Type','Column_Name', 'total_count', 'unique_count', 'null_count', 'null_Percent',
               'levels', 'value_count', 'counts_Percent']

        discrete_dataFrame = pd.DataFrame(columns=discrete_dataFrame_columns)



        def count_stats(column_data):
            total_count = column_data.count().compute()
            unique_count = column_data.nunique().compute()
            null_count = column_data.isnull().sum().compute()


            ## printing column counts
            #print('Total number of values : {}'.format(total_count))
            #print('Total number of unique values : {}'.format(unique_count))
            #print('Total number of null values : {}'.format(null_count))

            return total_count, unique_count, null_count



        for column in data_file.columns:

                #print("Working on : " + column)

                column_data = data_file[column]
                total_count, unique_count , null_count  = count_stats(column_data)
                if(total_count!=0):
                    null_per = float(null_count)/float(total_count)*100
                else:
                    null_per = 0

                #column_type,column_data = get_column_type(column_data)


                value_counts = pd.DataFrame(column_data.value_counts())
                value_counts = value_counts.reset_index()
                value_counts.insert(loc=0,column='Column_Name',value=column)
                value_count_columns = ['Column_Name','levels', 'value_count']
                value_counts.columns = value_count_columns
                value_counts = value_counts.sort_values(by='value_count', ascending=False)
                value_counts_top = value_counts[:10].copy()
                top_frequency = value_counts_top.value_count.sum()
                others_frequency = value_counts[10:].value_count.sum()


                temp_column_names = ['Column_Name','total_count','unique_count','null_count','null_Percent']
                temp_values = [[column,total_count,unique_count,null_count,null_per]]
                temp_dataFrame = pd.DataFrame(columns=temp_column_names,data=temp_values)

                ## create value counts dataframe with others column
                value_counts_top = value_counts_top.append(pd.DataFrame(columns=value_count_columns,data=[[column,'others',others_frequency]]))
                ## add null level
                value_counts_top = value_counts_top.append(pd.DataFrame(columns=value_count_columns,data=[[column,'nulls',null_count]]))
                ## add % counts

                if(total_count!=0):
                        value_counts_top['counts_Percent'] = value_counts_top.value_count/float(total_count) * 100
                else:
                        value_counts_top['counts_Percent'] = 0

                    ## merge temp_dataframe and value_counts_top, then insert into discrete_dataframe
                temp_discrete_dataFrame = temp_dataFrame.merge(how='left',left_on='Column_Name',right_on='Column_Name',right=value_counts_top)

                discrete_dataFrame = discrete_dataFrame.append(temp_discrete_dataFrame)
        discrete_dataFrame_cat = discrete_dataFrame.copy()
        discrete_dataFrame_cat['Column_Type']=['Categorical']*len(discrete_dataFrame_cat)        
        discrete_dataFrame_cat = discrete_dataFrame_cat[['Column_Type','Column_Name', 'total_count', 'unique_count', 'null_count', 'null_Percent',
               'levels', 'value_count', 'counts_Percent']]

        #### code for cont. data
        data_file = data.select_dtypes(include =np.number)
        def count_stats(column_data):
            total_count = column_data.count().compute()
            unique_count = column_data.nunique().compute()
            null_count = column_data.isnull().sum().compute()
            mean=column_data.mean().compute()
            std=column_data.std().compute()
            min_val=column_data.min().compute()
            max_val=column_data.max().compute()

            ## printing column counts
            #print('Total number of values : {}'.format(total_count))
            #print('Total number of unique values : {}'.format(unique_count))
            #print('Total number of null values : {}'.format(null_count))

            return total_count, unique_count, null_count, mean, std, min_val , max_val

        discrete_dataFrame_columns = ['Column_Type','Column_Name', 'total_count', 'unique_count', 'null_count', 'null_Percent',
               'levels', 'value_count', 'counts_Percent', 'mean', 'std', 'min',  'max']
        discrete_dataFrame = pd.DataFrame(columns=discrete_dataFrame_columns)



        def count_stats(column_data):
            total_count = column_data.count().compute()
            unique_count = column_data.nunique().compute()
            null_count = column_data.isnull().sum().compute()
            mean=column_data.mean().compute()
            std=column_data.std().compute()
            min_val=column_data.min().compute()
            max_val=column_data.max().compute()

            ## printing column counts
            #print('Total number of values : {}'.format(total_count))
            #print('Total number of unique values : {}'.format(unique_count))
            print('Total number of null values : {}'.format(null_count))

            return total_count, unique_count, null_count, mean, std, min_val , max_val




        for column in data_file.columns:

                #yprint("Working on : " + column)

                column_data = data_file[column]
                total_count, unique_count , null_count, mean, std, min_val, max_val = count_stats(column_data)
                if(total_count!=0):
                    null_per = float(null_count)/float(total_count)*100
                    #print("Not Null")
                else:
                    null_per = 0
                    #print("Null")

                #column_type,column_data = get_column_type(column_data)


                value_counts = pd.DataFrame(column_data.value_counts())
                value_counts = value_counts.reset_index()
                value_counts.insert(loc=0,column='Column_Name',value=column)
                value_count_columns = ['Column_Name','levels', 'value_count']
                value_counts.columns = value_count_columns
                value_counts = value_counts.sort_values(by='value_count', ascending=False)
                value_counts_top = value_counts[:10].copy()
                top_frequency = value_counts_top.value_count.sum()
                others_frequency = value_counts[10:].value_count.sum()


                temp_column_names = ['Column_Name','total_count','unique_count','null_count','null_Percent','mean','std','min','max']
                temp_values = [[column,total_count,unique_count,null_count,null_per,mean,std,min_val,max_val]]
                temp_dataFrame = pd.DataFrame(columns=temp_column_names,data=temp_values)

                ## create value counts dataframe with others column
                value_counts_top = value_counts_top.append(pd.DataFrame(columns=value_count_columns,data=[[column,'others',others_frequency]]))
                ## add null level
                value_counts_top = value_counts_top.append(pd.DataFrame(columns=value_count_columns,data=[[column,'nulls',null_count]]))
                ## add % counts

                if(total_count!=0):
                        value_counts_top['counts_Percent'] = value_counts_top.value_count/float(total_count) * 100
                else:
                        value_counts_top['counts_Percent'] = 0

                    ## merge temp_dataframe and value_counts_top, then insert into discrete_dataframe
                temp_discrete_dataFrame = temp_dataFrame.merge(how='left',left_on='Column_Name',right_on='Column_Name',right=value_counts_top)
                discrete_dataFrame = discrete_dataFrame.append(temp_discrete_dataFrame)


        discrete_dataFrame['Column_Type']=['Continous']*len(discrete_dataFrame)

        df3=discrete_dataFrame[['Column_Type','Column_Name', 'total_count', 'unique_count', 'null_count', 'null_Percent',
               'levels', 'value_count', 'counts_Percent', 'mean', 'std', 'min',  'max']]
        df3=df3.append(discrete_dataFrame_cat)


        #Adding required labels
        df3['Analysed_On']=pd.Timestamp.now()
        df3.insert(0, 'Datatable', m)
        df3.insert(0, 'Crypto', pair)
        final_data=final_data.append(df3)
        print("Appended to final DF",len(final_data))
        #print(df3)
        #_LOG.info(f"\nNo Issues Found in Analysis: {len(df3)}")	

    print("\nData Inserted to:",target_table)  
    return ssandown.RawData(final_data)
