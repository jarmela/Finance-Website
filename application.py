import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import datetime

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response


# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")

# Make sure API key is set
if not os.environ.get("API_KEY"):
    raise RuntimeError("API_KEY not set")


@app.route("/")
@login_required
def index():
    cash = db.execute("SELECT cash FROM users WHERE id=?",session["user_id"])[0]['cash']
    list1 = db.execute("SELECT stock, shares FROM stock_index WHERE show_username=?",session["user_id"])
    count= 0
    total = 0
    
    for i in list1:
        symbol = list1[count]['stock']
        value = lookup(symbol)
        i['value']= value['price']
        i['name']= value['name']
        i['total']= int(i['value']) * int(i['shares'])
        total = total + int(i['total'])
        i['total'] = str(i['total']) + ".00"
        count= count + 1
        
    total = int((cash) + total)
    total = str(total) + ".00"
    cash = str(cash) + ".00"

    global_list = [total, cash, list1]

    return render_template("index.html", global_list=global_list)


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    if request.method == "POST":
        
        if not request.form.get('symbol'):
            return apology("Symbol not entered", 400)
        elif not request.form.get('shares'):
            return apology("Shares not entered", 400)
        elif lookup(request.form.get('symbol')) == None:
            return apology("Symbol not valid", 400)
        if int(request.form.get('shares')) < 0: #or type(request.form.get('shares'))!= 'int':
            return apology("Nº of shares not valid", 400)
        
        price = int(lookup(request.form.get('symbol'))['price']) * int(request.form.get('shares'))
        
        if price > int(db.execute("SELECT cash FROM users WHERE id=?",session['user_id'])[0]['cash']):
            return apology("No money available", 400)

        db.execute("INSERT INTO stock('show_username', 'stock', 'shares', 'time', 'operation') VALUES(?,?,?,?,?)", session['user_id'],request.form.get('symbol'),request.form.get('shares'), datetime.now(), "Buy")
        db.execute("UPDATE users SET cash=? WHERE id=?", round(float(int(db.execute("SELECT cash FROM users WHERE id=?",session['user_id'])[0]['cash']) - price), 2) ,session['user_id'])
        
        
        #Atualizar a tabela que contem os dados para o index
        validade = True
        for i in db.execute("SELECT stock FROM stock_index WHERE show_username=?",session['user_id']):
            if request.form.get('symbol') == i['stock']:
                validade = False
                break
        if validade == True:
            db.execute("INSERT INTO stock_index('show_username', 'stock', 'shares') VALUES(?,?,?)", session['user_id'],request.form.get('symbol'),request.form.get('shares'))
        else:
            print(db.execute("SELECT shares FROM stock_index WHERE show_username=? AND stock=?",session['user_id'],request.form.get('symbol')))
            soma = round(float(int(db.execute("SELECT shares FROM stock_index WHERE show_username=? AND stock=?",session['user_id'],request.form.get('symbol'))[0]['shares']) + int(request.form.get('shares'))), 2)
            db.execute("UPDATE stock_index SET shares=? WHERE show_username=? AND stock=?",soma ,session['user_id'],request.form.get('symbol') )
            
        
        return redirect("/")
    else:
        return render_template('buy.html')


@app.route("/history")
@login_required
def history():
    list1 = db.execute("SELECT stock, shares, time, operation FROM stock WHERE show_username=?",session["user_id"])
    
    count= 0
    for i in list1:
        symbol = list1[count]['stock']
        value = lookup(symbol)
        i['value']= value['price']
        count= count + 1

    return render_template("history.html", list1=list1)
    
    


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

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
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    if request.method == "POST":
        if not request.form.get('symbol'):
            return apology("Symbol not entered", 400)
        else:
            symbol = request.form.get('symbol')
            if lookup(symbol) == None:
                return apology("Symbol not valid", 400)
            else:
                dic = lookup(symbol)
                return render_template('quoted.html', dic=dic)
    else:
        return render_template('quote.html')


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        
        if not request.form.get('username'):
            return apology("Username not entered", 400)
            
        elif not request.form.get('password'):
            return apology("Password not entered", 400)
            
        elif request.form.get('password') != request.form.get('confirmation'):
            return apology("Passwords do not correspond", 400)
            
        try:
            key = db.execute("INSERT INTO users ('username', 'hash') VALUES(?,?)",request.form.get('username'),  generate_password_hash(request.form.get('password')))
            
        except:
            return apology("Username already taken", 400)
            
        if key== None:
            return apology("Error", 400)
        session["user_id"] = key
        
        return redirect("/")
        
    return render_template("register.html")


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    if request.method == "POST":
        if not request.form.get('shares'):
            return apology("Nº of shares not entered", 400)
        if not request.form.get('symbol'):
            return apology("Symbol not entered", 400)
        if int(request.form.get('shares')) < 0:
            return apology("Nº of shares not valid", 400)
            
        n_shares_inpossess = int(db.execute("SELECT shares FROM stock_index WHERE show_username=? AND stock=?",session['user_id'],request.form.get('symbol'))[0]['shares'])
        if n_shares_inpossess == None or n_shares_inpossess < int(request.form.get('shares')):
             return apology("Nº of shares not valid", 400)
        
        price = round(float(int(lookup(request.form.get('symbol'))['price']) * int(request.form.get('shares'))),3)     
        db.execute("INSERT INTO stock('show_username', 'stock', 'shares', 'time', 'operation') VALUES(?,?,?,?,?)", session['user_id'],request.form.get('symbol'),request.form.get('shares'), datetime.now(), "Sell")
        db.execute("UPDATE users SET cash=? WHERE id=?", (int(db.execute("SELECT cash FROM users WHERE id=?",session['user_id'])[0]['cash']) + price) ,session['user_id'])
        
        
        #Atualizar a tabela que contem os dados para o index
        soma = round(float(int(db.execute("SELECT shares FROM stock_index WHERE show_username=? AND stock=?",session['user_id'],request.form.get('symbol'))[0]['shares']) - int(request.form.get('shares'))), 2)
        db.execute("UPDATE stock_index SET shares=? WHERE show_username=? AND stock=?",soma ,session['user_id'],request.form.get('symbol') )
        
        return redirect("/")
        
    
    else:
        list1 = db.execute("SELECT stock FROM stock_index WHERE show_username=?",session['user_id'])
        return render_template("sell.html", list1=list1)


def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)


