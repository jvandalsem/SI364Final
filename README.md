**Description**
This program utilizes Python's Flask Web Framework and allows users to search and save restaurants located in Ann Arbor through the Yelp Fusion API. After a response is provided and saved, users have the option to perform a few other tasks with these queried restaurants. Registered and logged in users can make a collection of restaurants, and can include/select all previously saved restaurants. Registered and logged in users can make a review about a restaurant/experience/meal, and sequentially rate the review on a scale from 1-5. Registered and logged in users can then view their own collections and reviews, and perform changes to both. Registered and logged in users can delete their own collections, and can update the rating of a restaurant review. All users can view all restaurants search from any of the users, along with the rating and price range of the restaurant(from Yelp API). Hope you enjoy. :)

**_Routes --> Templates_**
- 404 error handler --> 404.html
- /login --> all_posts.html
- /logout --> game_scores.html
- /register --> game_scores_view.html
- / --> index.html
- /all_restaurants --> all_restaurants.html
- /create_collection --> create_collection.html
- /user_collections --> user_collections.html
- /collection/<title> --> select_collection.html
- /delete/<id> --> user_collections.html
- /create_review --> create_review.html
- /user_reviews --> user_reviews.html
- /review/<id> --> review_list.html
- /update_review/<id> --> update_review.html
