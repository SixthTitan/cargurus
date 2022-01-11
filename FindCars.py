#!/usr/bin/env python3

# Author: Lauren Brown
# Program Name: Job Master
# Description: Finds available jobs and extracts data from a given keyword and notifies the user via SES
# @created: 7/26/2019
#
# from json5.lib import long

import emailer
from boto3.dynamodb.conditions import Attr
from bs4 import BeautifulSoup
import requests
import boto3
import schedule
import time
import datetime
import logging
import os
import re

"""
##################################################################
### Extract Data from Linkedin / Indeed and Post to DynamoDB  ####
##################################################################
"""

# Try to find the given attribute and return null if not found
def resolve_span(div, attr):
    try:
        rtn = div.find(name="span", attrs=attr)
        return rtn.text.strip()
    except:
        return None


def search_cargurus(url):
    # setup logging basic configuration for logging to a file
    logging.basicConfig(filename="cargurus.log")

    result = requests.get(url)
    content = result.content

    soup = BeautifulSoup(content, 'html.parser')

    # Current Time
    current_day = str(datetime.datetime.now().date())

    # DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')

    table = dynamodb.Table('dev-cars')

    for contents in soup.find_all('div', attrs={'class': 'listingSearchWrap'}):
        # Title
        title = contents.find('p', attrs={'class': 'detailsSection description'})
        photo = contents.find('picture')
        certified = contents.find('p', attrs={'class': 'detailsSection cpo'})
        transmission = contents.find('p', attrs={'class': 'detailsSection transmission'})
        color = contents.find('p', attrs={'class': 'detailsSection color'})
        price = contents.find('span', attrs={'class': 'price'})
        miles = contents.find('p', attrs={'class': 'mileage'})
        deal = contents.find('span', attrs={'class': 'dealLabel'})
        dealDifferential = contents.find('span', attrs={'class': 'dealDifferential'})
        owner = contents.find('div', attrs={'class': 'ownerName'})
        owner_date = contents.find('div', attrs={'class': 'date'})
        rating = contents.find('span', attrs={'class': 'ratingDetail'})
        phone = contents.find('div', attrs={'class': 'contactSellerWrapper'})

        link = contents.find('div', attrs={'class': 'cardBody'})

        number = (str(price.text.replace("$", "")))
        mile = (int(re.sub(",", "", number)))

        # print(rating.text)
        # print(title.span)
        # print(photo.img)
        # print(certified.span.text)
        # print(transmission.span.text)
        # print(color.span.text)
        # print(price.text)
        # print(miles.text)
        # print(deal.text)
        # print(dealDifferential.text)
        # print(owner.text)
        # print(owner_date.text)
        # print(phone.button.text)
        # print(link.a.get('href'))

        # print(str(price.text))

        max_miles = int(0)

        print(max_miles, "/", mile)

        # Only insert new real estate listing if it doesn't already exist
        conditions = Attr(phone.button.text).not_exists()

        # expires after one week
        expiryTimestamp = long(time.time() + 24 * 3600 * 7)

        url = """https://www.cargurus.com/Cars/inventorylisting/viewDetailsFilterViewInventoryListing.action?sourceContext=carGurusHomePageModel&entitySelectingHelper.selectedEntity=d2383&zip=12345""" + link.a.get(
            'href')
        picture = """<a href='""" + url + """'> <img src='""" + photo.img.get('src') + """'/> </a> """

        # Put the new job entry into DynamoDB for accessing later
        response = table.put_item(
            Item={
                'title': title.span.text,
                'photo': picture,
                'certified': certified.span.text,
                'transmission': transmission.text,
                'color': color.span.text,
                'price': price.text,
                'miles': miles.text,
                'deal': deal.text,
                'dealDifferential': dealDifferential.text,
                'owner': owner.text,
                'ownerDate': owner_date.text,
                'rating': rating.text,
                'phone': phone.button.text,
                'link': url,
                'date': current_day,
                'ttl': expiryTimestamp
            },
            ConditionExpression=conditions

        )

    entry = ('Added entry:',
             "Title: ", title.span.text,
             "Certified: ", certified.span.text,
             "Transmission: ", transmission.text,
             "Color: ", color.span.text,
             "Price: ", price.text,
             "Miles: ", miles.text,
             "Deal: ", deal.text,
             "dealDifferential: ", dealDifferential.text,
             "Owner: ", owner.text,
             "Rating: ", rating.text,
             "Phone: ", phone.button.text,
             "Link: ", url
             )
    print(entry)
    log_message = entry
    return logging.warning(log_message)


"""
###################################################################
#### Execute scheduled jobs and display current job queue      ####
###################################################################
"""


def scheduled_cars():
    cars_url = os.environ['url']

    search_cargurus(cars_url)


def scheduled_report():
    send_email()


"""
###################################################################
#### Send out a personalized e-mail with jobs to the user      ####
###################################################################
"""


def send_email():
    current_day = str(datetime.datetime.now().date())
    yesterday = str(datetime.datetime.now().date() - datetime.timedelta(hours=24))

    # Create our email Subject
    SUBJECT = "Latest Car Inventory: " + current_day

    # The email body for recipients with non-HTML email clients.
    BODY_TEXT = ("Daily Web Job Scraping\r\n"
                 "You cannot receive HTML emails, sorry. "
                 "Generated with AWS SDK for Python (Boto)."
                 )

    # Create our HTML body for HTML email clients
    body = """ <html> <body>
            <h1> Current Available Car Listings</h1>
            <p> Hi There, here's your daily car list matching your set keywords </p> """

    # DynamoDB
    dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
    table = dynamodb.Table('dev-cars')

    # Search for new job postings that were added to the DB between yesterday and today
    conditions = Attr('date').between(yesterday, current_day)

    response = table.scan(
        FilterExpression=conditions
    )

    for i in response['Items']:
        body += """
        
                <table>
                    <tr>
                        <th> <div align="left"> %s </div> </th>
                    </tr>
                    <tr>
                        <b> %s </b>
                    </tr>                     
                    <tr>
                        <b> Price: </b> %s  |  <b> Deal: </b> %s - %s 
                    </tr>                                                
                    <tr>
                        <b> Miles: </b> %s | <b> Color: </b> %s
                    </tr>
                      
                    <tr>
                        <b> Dealer Rating: </b> %s | <b> Phone: </b> %s <br /> <br />
                        <b> Link: </b> %s
                    </tr>  

                    
                <tr> <td> """ % (i['photo'],
                                 i['title'],
                                 i['price'],
                                 i['deal'],
                                 i['dealDifferential'],
                                 i['miles'],
                                 i['color'],
                                 i['rating'],
                                 i['phone'],
                                 i['link']

                                 ) + """ </td> </tr> 
                
                """

    # End the body with final closing markers
    body += """ 
        </body>
        </html>
        """

    # Send the email with given parameters
    emailer.ses_email(SUBJECT, BODY_TEXT, body, os.environ['email'], os.environ['email'])


"""
######################################
#### Setup and Run Scheduled Jobs ####
######################################
"""

# scheduled_report()

scheduled_cars()

schedule.every().day.at("16:00").do(scheduled_report)

schedule.every(30).minutes.do(scheduled_cars)  # Get new car listings every half hour from carguru

while True:
    schedule.run_pending()
    time.sleep(1)
