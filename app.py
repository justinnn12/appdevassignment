from flask import Flask, render_template, request, redirect, url_for, make_response, flash
from flask_wtf.file import FileField, FileAllowed
from Forms import CreateProductForm
from werkzeug.utils import secure_filename
import shelve, Product, os

app = Flask(__name__)


def get_user():
    with shelve.open('user_cred.db', 'c') as db:
        return db.get('Users', {})


def save_user(users):
    with shelve.open('user_cred.db', 'w') as db:
        db['Users'] = users


def get_each_cart(username):
    with shelve.open('get_cart.db', 'c') as db:
        return db.get(username, [])


def save_each_cart(username, each_cart):
    with shelve.open('get_cart.db', 'w') as db:
        db[username] = each_cart


@app.context_processor
def inject_user():
    username = request.cookies.get('username')
    return dict(username=username)


@app.route('/')
def home():
    if not os.path.exists('product.db'):  # check if db exist or not
        # Open the existing database and check if 'Products' exists
        with shelve.open('product.db', 'c') as db:
            product_dict = db.get('Products', {})  # Default to empty dict if 'Products' doesn't exist

    product_list = list(product_dict.values())
    current_user = request.cookies.get('username')

    return render_template('retrieveProducts.html', count=len(product_list), product_list=product_list,
                                                    username=current_user if current_user else None)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = get_user()
        if username in users and users[username] == password:
            resp = make_response(redirect(url_for('home')))
            resp.set_cookie('username', username)
            return resp
        else:
            return 'Invalid username or password!'
    return render_template('login.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        users = get_user()
        if username in users:
            return 'User already exists, please log in'
        users[username] = password
        save_user(users)

        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/logout')
def logout():
    resp = make_response(redirect(url_for('home')))
    resp.delete_cookie('username')
    return resp


@app.route('/profile', methods=['GET', 'POST'])
def profile():
    current_user = request.cookies.get('username')

    if not current_user:
        return redirect(url_for('login'))

    if request.method == 'POST':
        if 'new_username' in request.form:
            new_username = request.form['new_username']
            with shelve.open('user_cred.db', 'c') as db:
                users = db.get('Users', {})
                users[new_username] = users.pop(current_user)
                db['Users'] = users

            resp = make_response(redirect(url_for('profile')))
            resp.set_cookie('username', new_username)
            return resp

        if 'new_password' in request.form:
            new_password = request.form['new_password']

            with shelve.open('user_cred.db', 'c') as db:
                users = db.get('Users', {})
                print(f"current user: {current_user}")
                users[current_user]= new_password
                db['Users'] = users

    with shelve.open('user_cred.db', 'r') as db:
        users = db.get('Users', {})
        user_details = users.get(current_user, {})

    return render_template('profile.html', user_details=user_details)


upload_folder = 'static/uploads/'
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)  # create the folder if dont exist
# app.config['UPLOAD_FOLDER'] = 'static/uploads/'


@app.route('/createProduct', methods=['GET', 'POST'])
def create_product():
    create_product_form = CreateProductForm(request.form)  # call the form to create a new product
    if request.method == 'POST' and create_product_form.validate():  # if the form is valid
        product_dict = {}
        db = shelve.open('product.db', 'w')

        try:
            product_dict = db['Products']
        except:
            print('Error in retrieving products from product.db')

        product_dict = db.get('Products', {})  # get product dict from db, if not make an empty one
        last_product_id = db.get('last_product_id', 0)  # retrieve the last product id

        image_filename = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename:
                # Use the original filename directly
                image_filename = file.filename
                file.save(os.path.join('static/uploads/', image_filename))

        product = Product.Product(create_product_form.product_name.data,
                                  create_product_form.description.data,
                                  create_product_form.price.data,
                                  create_product_form.category.data,
                                  create_product_form.condition.data,
                                  create_product_form.remarks.data,
                                  image_filename=image_filename
                                  )
        product_dict[product.get_product_id()] = product  # add the product to product_dict
        db['Products'] = product_dict

        db['last_product_id'] = last_product_id + 1
        db.close()

        return redirect(url_for('home'))
    return render_template('createProduct.html', form=create_product_form)


@app.route('/retrieveProducts')
def retrieve_products():
    role = request.args.get('role', 'staff')  # default to staff view
    product_dict = {}
    db = shelve.open('product.db', 'r')
    product_dict = db['Products']
    db.close()

    product_list = []
    for key in product_dict:
        product = product_dict.get(key)
        product_list.append(product)

    return render_template('retrieveProducts.html', count=len(product_list), product_list=product_list, role=role)


@app.route('/updateProduct/<int:id>/', methods=['GET', 'POST'])
def update_product(id):
    update_product_form = CreateProductForm(request.form)
    if request.method == 'POST' and update_product_form.validate():
        product_dict = {}
        db = shelve.open('product.db', 'w')
        product_dict = db['Products']

        product = product_dict.get(id)
        product.set_name(update_product_form.product_name.data)
        product.set_description(update_product_form.description.data)
        product.set_price(update_product_form.price.data)
        product.set_category(update_product_form.category.data)
        product.set_condition(update_product_form.condition.data)
        product.set_remarks(update_product_form.remarks.data)

        db['Products'] = product_dict
        db.close()

        return redirect(url_for('retrieve_products'))
    else:
        product_dict = {}
        db = shelve.open('product.db', 'r')
        product_dict = db['Products']
        db.close()

        product = product_dict.get(id)
        update_product_form.product_name.data = product.get_product_name()
        update_product_form.description.data = product.get_description()
        update_product_form.price.data = product.get_price()
        update_product_form.category.data = product.get_category()
        update_product_form.remarks.data = product.get_remarks()

        return render_template('updateProduct.html', form=update_product_form)


@app.route('/deleteProduct/<int:id>', methods=['POST'])
def delete_product(id):
    product_dict = {}
    db = shelve.open('product.db', 'w')
    product_dict = db['Products']

    product_dict.pop(id)

    db['Products'] = product_dict
    db.close()

    return redirect(url_for('retrieve_products'))


@app.route('/viewProduct/<int:id>')
def view_product(id):
    db = shelve.open('product.db', 'r')
    product_dict = db.get('Products', {})
    db.close()

    product = product_dict.get(id)

    if not product:
        return redirect(url_for('retrieve_products'))
    return render_template('viewProduct.html', product=product)


@app.route('/add_to_cart/<int:id>', methods=['POST'])
def add_to_cart(id):
    current_user = request.cookies.get('username')

    if current_user:
        with shelve.open('product.db', 'c') as db:
            # product_dict = db.get('Products', {})
            user_carts = db.get('Carts', {})
            cart_list = user_carts.get(current_user, [])

            if id not in cart_list:
                cart_list.append(id)

            user_carts[current_user] = cart_list
            db['Carts'] = user_carts  # save this to the cart

    return redirect(url_for('view_cart'))


@app.route('/view_cart')
def view_cart():
    current_user = request.cookies.get('username')

    if not current_user:
        return redirect(url_for('login'))

    with shelve.open('product.db', 'r') as db:
        # db = shelve.open('product.db', 'r')
        user_carts = db.get('Carts', {})
        cart_list = user_carts.get(current_user, [])  # retrieve from the cart
        product_dict = db.get('Products', {})

    cart_items = []  # create empty list for items in cart
    total_price = 0
    for product_id in cart_list:
        if product_id in product_dict:
            product = product_dict[product_id]
            cart_items.append(product_dict[product_id])
            total_price += product.get_price()

    return render_template('view_cart.html', cart_list=cart_items, total_price=total_price, username=current_user)


@app.route('/remove_from_cart/<int:product_id>', methods=['POST'])
def remove_from_cart(product_id):
    current_user = request.cookies.get('username')

    if current_user:
        with shelve.open('product.db', 'r') as db:
            user_cart = db.get('Carts', {})
            cart_list = user_cart.get(current_user, [])  # retrieve product ids
            # product_dict = db.get('Products', {})

        for cart_item in cart_list:
            if product_id == cart_item:
                cart_list.remove(cart_item)
        # if product_id in cart_list:
        #     cart_list.remove(product_id)

        with shelve.open('product.db', 'w') as db:
            user_cart[current_user] = cart_list
            db['Carts'] = user_cart  # save the new cart

    return redirect(url_for('view_cart'))


# @app.route('/clear_cart', methods=['POST'])
# def clear_cart():
#     db = shelve.open('product.db', 'c')
#     db['Cart'] = []  # Clear the cart
#     db.close()
#
#     return redirect(url_for('view_cart'))
#
#
# @app.route('/checkout', methods=['POST'])
# def checkout():
#     db = shelve.open('product.db', 'c')
#     db['Cart'] = []  # Empty the cart after checkout
#     db.close()
#
#     return redirect(url_for('retrieve_products'))


if __name__ == '__main__':
    app.run(debug=True)