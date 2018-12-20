# *** Final Project application about Ann Arbor Restaurants ***

# Flask/Database Imports
import os
from flask import Flask, render_template, session, redirect, request, url_for, flash
from flask_script import Manager, Shell
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, FloatField, PasswordField, BooleanField, SelectMultipleField, ValidationError, IntegerField, TextAreaField
from wtforms.validators import Required, Length, Email, Regexp, EqualTo
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate, MigrateCommand
from werkzeug.security import generate_password_hash, check_password_hash
# Loging Management Imports
from flask_login import LoginManager, login_required, logout_user, login_user, UserMixin, current_user
from werkzeug.security import generate_password_hash, check_password_hash

# Libraries code from Yelp Fusion Github -> https://github.com/Yelp/yelp-fusion/blob/master/fusion/python/sample.py#L38
import json
import requests
import urllib
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.parse import urlencode

# Configure base directory of application
basedir = os.path.abspath(os.path.dirname(__file__))

# Application configurations
app = Flask(__name__)
app.debug = True
app.config['SECRET_KEY'] = 'super hard to guess string for jvd and jvd alone'
app.config["SQLALCHEMY_DATABASE_URI"] = "postgresql://localhost/jjvandal364finaldb" # Database creation
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Yelp Fusion API Setup
api_key =  'iraxmD5cfPeHdi5st7Bl-4__sc-tet0s7G48wr1KxMFFiOaKxoh7Gr7zBRuLQKkkto_tKalHwF69UPi5AuNYwX3I2aWmc49j_5fcy7olHfyd9K0WYUZ0QLCMF04YXHYx'
base_url = 'https://api.yelp.com'
base_headers = {'Authorization': 'Bearer %s' % api_key} #From Yelp Fusion Github -> https://github.com/Yelp/yelp-fusion/blob/master/fusion/python/sample.py#L38

# DB Objects Setup
manager = Manager(app)
db = SQLAlchemy(app)
migrate = Migrate(app, db)
manager.add_command('db', MigrateCommand)

# Login Configuration Setup
login_manager = LoginManager()
login_manager.session_protection = 'strong'
login_manager.login_view = 'login'
login_manager.init_app(app) # set up login manager

##################################################################################################################

### MODELS ###

# Association Table

user_collection = db.Table('user_collection',
    db.Column('restaurant_id', db.Integer,db.ForeignKey('restaurants.id')),
    db.Column('collection_id', db.Integer, db.ForeignKey('restaurant_collections.id')))

# User Models

# From HW4
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    username = db.Column(db.String(255), unique = True, index = True)
    email = db.Column(db.String(64), unique = True, index = True)
    password_hash = db.Column(db.String(128))
    restaurant_collections = db.relationship('RestaurantCollection', backref = 'users', lazy = 'dynamic')
    reviews = db.relationship('UserReview', backref = 'users', lazy = 'dynamic')

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

# DB Load Function
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key = True)
    name = db.Column(db.String())
    rating = db.Column(db.Float())
    price = db.Column(db.Integer())
    response_id = db.Column(db.String())

class RestaurantCollection(db.Model):
    __tablename__ = 'restaurant_collections'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(), unique = True)
    user = db.Column(db.Integer, db.ForeignKey('users.id'))
    restaurants = db.relationship('Restaurant', secondary = user_collection, backref = db.backref('restaurant_collections', lazy = 'dynamic'), lazy = 'dynamic')

class UserReview(db.Model):
    __tablename__ = 'user_review'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(), unique = True)
    text = db.Column(db.String())
    rating = db.Column(db.Integer())
    user = db.Column(db.Integer, db.ForeignKey('users.id'))


##################################################################################################################

## FORMS ###
def validate_user_search(form, field):
    restaurant_response = get_restaurant_api(field.data)
    if len(restaurant_response) == 0:
        raise ValidationError('No restaurants matched your search. Make sure the restaurant is located in Ann Arbor!')

def validate_review_rating(form, field):
    rating = int(field.data)
    if rating not in range(1,6) or type(field.data) != type(1):
        raise ValidationError('Could not save rating. Must enter digit from 1-5')

# HW4 User Registration Form
class RegistrationForm(FlaskForm):
    email = StringField('Email:', validators=[Required(),Length(1,64),Email()])
    username = StringField('Username:',validators=[Required(),Length(1,64),Regexp('^[A-Za-z][A-Za-z0-9_.]*$',0,'Usernames must have only letters, numbers, dots or underscores')])
    password = PasswordField('Password:',validators=[Required(),EqualTo('password2',message="Passwords must match")])
    password2 = PasswordField("Confirm Password:",validators=[Required()])
    submit = SubmitField('Register User')

    def validate_email(self,field):
        if User.query.filter_by(email=field.data).first():
            raise ValidationError('Email already registered.')

    def validate_username(self,field):
        if User.query.filter_by(username=field.data).first():
            raise ValidationError('Username already taken')

# HW4 User Login Form
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[Required(), Length(1,64), Email()])
    password = PasswordField('Password', validators=[Required()])
    remember_me = BooleanField('Keep me logged in')
    submit = SubmitField('Log In')

class RestaurantSearchForm(FlaskForm):
    search = StringField('Search for an Ann Arbor restaurant: ', validators=[Required(), validate_user_search])
    submit = SubmitField('Search')

class CollectionCreateForm(FlaskForm):
    title = StringField('New restaurant collection title: ',validators=[Required()])
    restaurant_choices = SelectMultipleField('Select restaurants to include ', validators = [Required()], coerce=int)
    submit = SubmitField('Create Restaurant Collection')

class ReviewForm(FlaskForm):
    title = StringField('New restaurant review title: ', validators = [Required()])
    text = TextAreaField('Enter your review: ', validators = [Required()])
    rating = IntegerField('Enter your review rating: (1-5)', validators = [Required(), validate_review_rating])
    submit = SubmitField('Post')

class UpdateButtonForm(FlaskForm):
    submit = SubmitField('Update Rating')

class UpdateRatingForm(FlaskForm):
    rating = IntegerField('Change the rating of this restaurant review: (still 1-5)', validators = [Required(), validate_review_rating])
    submit = SubmitField('Submit')

class DeleteButtonForm(FlaskForm):
    submit = SubmitField('Delete')

##################################################################################################################

### HELPER FXNS ###

# Yelp Fusion API call function
def get_restaurant_api(user_query):
    id_route = '/v3/businesses/search'
    id_params = {'term': user_query.replace(' ', '+'), 'location': 'Ann Arbor'}
    id_url = '{0}{1}'.format(base_url, quote(id_route.encode('utf8'))) #From Yelp Fusion Github -> https://github.com/Yelp/yelp-fusion/blob/master/fusion/python/sample.py#L38
    id_response = requests.request('GET', id_url, headers = base_headers, params = id_params)
    return id_response.json()['businesses']

def get_restaurant_by_id(id):
    restaurant = Restaurant.query.filter_by(id = id).first()
    return restaurant

def get_or_create_restaurant(user_query):
    restaurant = Restaurant.query.filter_by(name = user_query).first()
    if restaurant:
        print('Found restaurant')
        return restaurant
    else:
        restaurant_data = get_restaurant_api(user_query)
        name = str(restaurant_data[0]['name'])
        rating = restaurant_data[0]['rating']
        price = len(str(restaurant_data[0]['price']))
        response_id = str(restaurant_data[0]['id'])
        restaurant = Restaurant(name = name, rating = rating, price = price, response_id = response_id)
        db.session.add(restaurant)
        db.session.commit()
        print('Added restaurant')
        return restaurant

def get_or_create_collection(title, current_user, restaurants_l=[]):
    collection = current_user.restaurant_collections.filter_by(title=title).first()
    if collection:
        return collection
    else:
        collection = RestaurantCollection(title = title)
        current_user.restaurant_collections.append(collection)
        for a in restaurants_l:
            collection.restaurants.append(a)
        db.session.add(current_user)
        db.session.add(collection)
        db.session.commit()
        return collection

def get_or_create_review(title, text, rating, current_user):
    review = UserReview.query.filter_by(title=title).first()
    if review:
        return review
    else:
        review = UserReview(title=title, text=text, rating = int(rating))
        current_user.reviews.append(review)
        db.session.add(current_user)
        db.session.add(review)
        db.session.commit()
        return review

##################################################################################################################

### View Functions ###

# Error handling routes
@app.errorhandler(404)
def page_not_found(error):
    return render_template('404.html')

## Login-related routes - provided
@app.route('/login',methods=["GET","POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('index'))
        flash('Invalid username or password.')
    return render_template('login.html',form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out')
    return redirect(url_for('index'))

@app.route('/register',methods=["GET","POST"])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('You can now log in!')
        return redirect(url_for('login'))
    return render_template('register.html',form = form)

# Relevant application routes
@app.route('/', methods=['GET', 'POST'])
def index():
    form = RestaurantSearchForm()
    if form.validate_on_submit():
        user_search = form.search.data
        get_or_create_restaurant(user_search)
        flash('Added restaurant')
        return redirect(url_for('index'))
    form_errors = [a for a in form.errors.values()]
    for a in form_errors:
        flash('Error in form submission: ' + str(a[0]))
    return render_template('index.html',form = form)

@app.route('/all_restaurants')
def all_restaurants():
    all_restaurants = Restaurant.query.all()
    return render_template('all_restaurants.html', all_restaurants = all_restaurants)

@app.route('/create_collection',methods=['GET', 'POST'])
@login_required
def create_collection():
    form = CollectionCreateForm()
    restaurant_choices = [(a.id, a.name) for a in Restaurant.query.all()]
    form.restaurant_choices.choices = restaurant_choices
    if form.validate_on_submit():
        restaurant_picks = form.restaurant_choices.data
        restaurants_l = [get_restaurant_by_id(id) for id in restaurant_picks]
        get_or_create_collection(title = form.title.data, current_user = current_user, restaurants_l = restaurants_l)
        return redirect(url_for('user_collections'))
    return render_template('create_collection.html',form = form)

@app.route('/user_collections',methods=['GET','POST'])
@login_required
def user_collections():
    form = DeleteButtonForm()
    user_collections = current_user.restaurant_collections.all()
    return render_template('user_collections.html', user_collections = user_collections, form = form)

@app.route('/collection/<title>')
@login_required
def select_collection(title):
    title = str(title)
    collection = RestaurantCollection.query.filter_by(title = title).first()
    restaurants = collection.restaurants.all()
    return render_template('select_collection.html', collection = collection, restaurants = restaurants)

@app.route('/delete/<id>',methods=['GET','POST'])
@login_required
def delete_collection(id):
    del_collection = RestaurantCollection.query.filter_by(id = id).first()
    db.session.delete(del_collection)
    db.session.commit()
    flash('Successfully deleted collection: \'' + del_collection.title + '\'')
    return redirect(url_for('user_collections'))

@app.route('/create_review', methods=['GET','POST'])
@login_required
def create_review():
    form = ReviewForm()
    if form.validate_on_submit():
        title = form.title.data
        text = form.text.data
        rating = form.rating.data
        get_or_create_review(title = title, text = text, rating = int(rating), current_user = current_user)
        return redirect(url_for('user_reviews'))
    form_errors = [a for a in form.errors.values()]
    for a in form_errors:
        flash('Error in form submission: ' + str(a[0]))
    return render_template('create_review.html',form=form)

@app.route('/user_reviews', methods=['GET','POST'])
@login_required
def user_reviews():
    user_reviews = current_user.reviews.all()
    return render_template('user_reviews.html', user_reviews = user_reviews)

@app.route('/review/<id>', methods=['GET','POST'])
def single_review(id):
    form = UpdateButtonForm()
    review = UserReview.query.filter_by(id=id).first()
    return render_template('review_list.html',review=review, form=form)

@app.route('/update_review/<id>', methods=["GET","POST"])
def update_review(id):
    form = UpdateRatingForm()
    review = UserReview.query.filter_by(id = id).first()
    if form.validate_on_submit():
        upd_rating = form.rating.data
        review.rating = upd_rating
        db.session.add(current_user)
        db.session.add(review)
        db.session.commit()
        flash('Updated rating of: \'' + review.title + '\'')
        return redirect(url_for('single_review', id = id))
    form_errors = [a for a in form.errors.values()]
    for a in form_errors:
        if str(a[0]) == 'Could not save rating. Must enter digit from 1-5':
            flash('Error in form submission: ' + str(a[0]))
    return render_template('update_review.html', form = form, review = review)

if __name__ == '__main__':
    db.create_all()
    manager.run()
