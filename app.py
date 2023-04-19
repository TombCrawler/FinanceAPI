import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


@app.route("/")
@login_required
def index():
    # get data from tables stocks for a specific user, then assign to rows, rows is a dictionary
    rows = db.execute("SELECT * FROM stocks WHERE user_id = ?", session["user_id"])
    # create a new LIST
    stocks = []

    # Get cash from table, users
    # db.execute will return a list of zero or more dictionaries
    # [0] near the end of lines 55 indicate that get the first dictionary in the list
    cash = db.execute("SELECT cash FROM users WHERE id = ?", session["user_id"])[0]["cash"]

    # new variable and get value from cash
    # cash is the balance, total is sum of cash and all the symbols with their prices at the moment(not the price when they bought)
    balance_total = cash

    # loop through each dictionary in rows
    for row in rows:
        # get data from lookup
        stock = lookup(row["symbol"])

        # What data we need to append to stocks
        # 1. symbol: we can get it from row
        # 2. name : we can get it by using lookup() with the symbol from .1
        # 3. shares: we can get it from row
        # 4. price: same at .2 can get from lookup
        # 5. total: .3 times .4
        stocks.append({'symbol': stock["symbol"], 'name': stock["name"], 'shares': row["shares"],
                      'price': stock["price"], 'total': row["shares"] * stock["price"]})
        # increase total amount by amount from .5
        balance_total = balance_total + (row["shares"] * stock["price"])

    # pass stocks list, cash and total to HTML for display
    return render_template("index.html", stocks=stocks, balance_total=balance_total, cash=cash)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    # get symbol
    if request.method == "POST":
        symbol = request.form.get("symbol")
        if not symbol:
            return apology("Symbol Required!", 400)
        stock = lookup(symbol)
        if not stock:
            return apology("Symbol Not Found")
        else:
            user_id = session["user_id"]

        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Invalid Share", 400)
        price = stock["price"]
        price = float(price)
        totalAmount = price * shares
        row = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cashLeft = row[0]["cash"]

        if not shares:
            return apology("Share Number Required!", 400)

        elif totalAmount > cashLeft or shares < 1:
            return apology("Insufficient Fund or Share Number Required")

        else:
            db.execute("INSERT INTO transactions (user_id, price, symbol, shares,\
                       transaction_type) VALUES(?, ?, ?, ?, ?) ", user_id, price, symbol, shares, "buy")
            # this is for I want to know which symbol they own
            rows = db.execute("SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", user_id, symbol)
            # this means the symbol already existed
            if len(rows) >= 1:
                # this is for to UPDATE the stocks table
                db.execute("UPDATE stocks SET shares = ? WHERE user_id = ?\
                           AND symbol = ?", shares + rows[0]["shares"], user_id, symbol)

            else:
                db.execute("INSERT INTO stocks (user_id, symbol, shares) VALUES(?, ?, ?)", user_id, symbol, shares)

            db.execute("UPDATE users SET cash = ? WHERE id = ?", cashLeft - totalAmount, user_id)
            return redirect("/")

    else:

        return render_template("buy.html")


@app.route("/history", methods=["GET", "POST"])
@login_required
def history():

    if request.method == "POST":
       user_id = session["user_id"]
       db.execute("DELETE FROM transactions WHERE user_id = ?", user_id)

       return redirect("/history")

    else:
        user_id = session["user_id"]
        histories = db.execute("SELECT * FROM transactions WHERE user_id = ?", user_id)
        return render_template("history.html", histories=histories)


@app.route("/login", methods=["GET", "POST"])
def login():

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":

        try:
            symbol = request.form.get("symbol")
            stock = lookup(symbol)
            symbol = stock["symbol"]
            name = stock["name"]
            price = stock["price"]

            price = usd(price)
            return render_template("quoted.html", symbol=symbol, name=name, price=price)

        except TypeError:
            return apology(("Symbol Not Found"))

    else:
        return render_template("quote.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hash = generate_password_hash(password)
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        if not request.form.get("username") or not request.form.get("password")\
                or request.form.get("password") != request.form.get("confirmation") \
                or len(rows) >= 1:
            return apology("Invalid Username or Password")

        else:
            db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)
            return redirect("/register")

    else:
        return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        symbol = request.form.get("symbol")
        try:
            shares = int(request.form.get("shares"))
        except:
            return apology("Invalid Share", 400)
        user_id = session["user_id"]
        symbol = request.form.get("symbol")
        row1 = db.execute("SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", user_id, symbol)
        shares_owned = row1[0]["shares"]
        stock = lookup(symbol)
        price = stock["price"]
        price = float(price)
        totalAmount = price * shares
        rows1 = db.execute("SELECT cash FROM users WHERE id = ?", user_id)
        cashLeft = rows1[0]["cash"]

        if not shares:
            return apology("Share Number Required!", 400)

        elif shares_owned < shares:
            return apology("Too many shares!", 400)

        else:
            db.execute("INSERT INTO transactions (user_id, price, symbol, shares,\
                       transaction_type) VALUES (?, ?, ?, ?, ?)", user_id, price, symbol, shares, "sell")
            rows2 = db.execute("SELECT * FROM stocks WHERE user_id = ? AND symbol = ?", user_id, symbol)

            if len(rows2) >= 1:
                db.execute("UPDATE stocks SET shares = ? WHERE user_id = ? AND symbol = ?", shares_owned - shares, user_id, symbol)
                user_id = session["user_id"]
                db.execute("DELETE FROM stocks WHERE user_id = ? AND shares = 0", user_id)
                db.execute("UPDATE users SET cash = ? WHERE id = ?", totalAmount + cashLeft, user_id)
                return redirect("/")

    else:
        request.method == "GET"
        symbol = request.form.get("symbol")

        # This section is for get symbols which user own on drop down menue
        user_id = session["user_id"]
        # symbol is a list contains [{'symbol':'nflx'}, {'symbol'}: 'a', {'symbol':'amzn'}, {'symbol':'e'}]
        symbol = db.execute("SELECT symbol FROM stocks WHERE user_id = ?", user_id)
        return render_template("sell.html", symbol=symbol)


