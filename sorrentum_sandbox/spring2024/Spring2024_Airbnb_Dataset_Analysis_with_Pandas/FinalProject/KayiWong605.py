#KayiWong 605 Project
import numpy as np
import pandas as pd
import tkinter as tk
import matplotlib
import matplotlib.pyplot as plt
matplotlib.use('Agg')


# Read the dataset
root=tk.Tk()
Property_details = pd.read_csv('/app/FinalProject/Property_details.csv', index_col=0, encoding='utf-8')
Order_details = pd.read_csv('/app/FinalProject/Order_details.csv', index_col=0, encoding='ISO-8859-1')

# 1
# Create a new column called "weekday", which is the day of the “reservation date” in one week
Order_details['reservation date'] = pd.to_datetime(Order_details['reservation date']) 
Order_details['weekday'] = Order_details['reservation date'].dt.day_name()
# Find weekdays with above-average reservations
wkday_reservations = Order_details.groupby('weekday')['weekday'].count()
wkday_reservations.head()
avg_reservations = wkday_reservations.mean()
avg_reservations
above_avg_weekdays=wkday_reservations[wkday_reservations > avg_reservations]
print("Weekdays with above-average reservations:")
print(above_avg_weekdays)

# 2
# Find 10 most & least common room amennities and their percentage of total reservations
amenities=Order_details['roomamenities'].str.split(': ;').dropna()
amenity_counts=pd.Series([amenity for sublist in amenities for amenity in sublist if amenity]).value_counts()

top_10_common=amenity_counts.head(10)

least_10_common=amenity_counts.tail(10)

print("10 most common room amenities:")
print(top_10_common)
print("\n10 least common room amenities:")
print(least_10_common)

amenity_percentage=(amenity_counts/len(Order_details))*100

print("\nPercentage of each room amenity of the total num of reservations:")
print(amenity_percentage)

# 3
# Some 'onsiteprice' are marked as 0, which is wrong. I created a new column called 'replaced onsiteprice'. This column replaces the 0 value with median of non-zero “onsiteprice”.
# For each property, I calculated the maximum and minimum value of “replaced onsiteprice” and put them in "Maximum" and "Minimum".I stored them in 'Max_Min_Price.csv'.
price_NonZero=Order_details.loc[Order_details['onsiteprice']!=0]
price_NonZero['replaced onsiteprice']=price_NonZero.onsiteprice.copy()
median_non=price_NonZero.groupby(by='propertycode')['onsiteprice'].median()

price_Zero=Order_details.loc[Order_details['onsiteprice']==0]
price_Zero=pd.merge(price_Zero,median_non,how='left',on='propertycode')
price_Zero.rename(columns={'onsiteprice_y':'replaced onsiteprice'},inplace=True)
price_all=pd.concat([price_NonZero,price_Zero])
price_all.drop('onsiteprice_x',axis=1,inplace=True)

P_4=price_all.groupby(by=['propertycode'])
agg_4=P_4.agg(Minimum=('replaced onsiteprice',np.min),Maximum=('replaced onsiteprice',np.max))
agg_4.to_csv('Max_Min_Price.csv')
agg_4


# 4
# Find average star rating for each country
country_rating=(Property_details
                  .groupby('country')['starrating']
                  .mean()
                  .sort_values(ascending=False)
                  .reset_index())
fig,ax=plt.subplots()
country_rating.plot(kind='barh',x='country',y='starrating', color='g', ax=ax)

ax.set_title('Average Star Rating of Different Country')
ax.set_xlabel('Star Rating')
ax.set_ylabel('Country')

average_rating=country_rating['starrating'].mean()
ax.axvline(x=average_rating,color='b',linestyle='--',label='Average')

ax.annotate(f'Average Star Rating={average_rating:.2f}',xy=(average_rating,20))

ax.legend().set_visible(False)

plt.savefig('/app/FinalProject/avg_star_rating.png') 


# 5
# Find the 5 most popular room types and their repective proportion
roomtype_num_most=(Order_details.groupby('roomtype')['propertycode'].count().sort_values(ascending=False).reset_index().head(5))
total_orders=Order_details['propertycode'].count()
roomtype_num_most['proportion']=roomtype_num_most['propertycode']/total_orders
roomtype_num_most

room_counts=roomtype_num_most['propertycode']
room_labels=roomtype_num_most['roomtype']

fig, ax = plt.subplots(figsize=(10, 6))
ax.bar(room_labels, room_counts, color='skyblue')
ax.set_title('Most Popular 5 Room Type Proportion')
ax.set_xlabel('Room Type')
ax.set_ylabel('Counts')
plt.xticks(rotation=45)
plt.tight_layout() 
plt.savefig('/app/FinalProject/5_popular.png')
 


# 6
# Find average discount in each month
Month_discount=(Order_details
                  .groupby(Order_details['reservation date'].dt.month)
                  .discount
                  .mean()
                  .reset_index()
                  .rename(columns={'reservation date':'Month','discount':'Average Discount'})
                  .sort_values(by='Average Discount',ascending=False))
Month_discount

plt.figure(figsize=(10, 6))
plt.bar(Month_discount['Month'], Month_discount['Average Discount'], color='skyblue')
plt.xlabel('month')
plt.ylabel('avg discount')
plt.xticks(Month_discount['Month'])
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.savefig('/app/FinalProject/avg_discount.png') 

# 7
# Find top 5 countries with properties having star rating over 3.5
properties_above_3_5 = Property_details[Property_details['starrating'] > 3.5]
top_countries = properties_above_3_5['country'].value_counts().head(5)
print(top_countries)

plt.figure(figsize=(8, 6))
top_countries.plot(kind='bar', color='skyblue')
plt.title('Top 5 Countries with Properties having Star Rating over 3.5')
plt.xlabel('Country')
plt.ylabel('Number of Properties')
plt.xticks(rotation=45)
plt.savefig('/app/FinalProject/top_5.png') 

# 8
# Find the average on site price of each room occupancy
average_price_per_occupancy = Order_details.groupby('maxoccupancy')['onsiteprice'].mean().reset_index()
average_price_per_occupancy = average_price_per_occupancy.rename(columns={'onsiteprice': 'Average Onsite Price'})
print(average_price_per_occupancy)

plt.figure(figsize=(10, 6))
plt.bar(average_price_per_occupancy['maxoccupancy'], average_price_per_occupancy['Average Onsite Price'], color='skyblue')
plt.xlabel('Max Occupancy')
plt.ylabel('Average Onsite Price')
plt.title('Average Onsite Price by Occupancy')
plt.xticks(average_price_per_occupancy['maxoccupancy'])
plt.savefig('/app/FinalProject/avg_onsite.png') 


