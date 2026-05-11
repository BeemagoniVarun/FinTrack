from flask import Flask, render_template, redirect, url_for, flash, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from models import db, User, Expense
from forms import RegisterForm, LoginForm, ExpenseForm
from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import os

# -------------------- SUMMARY QUERIES --------------------
def get_summary():
    # Monthly total for May 2026
    monthly_total = db.session.query(db.func.sum(Expense.amount))\
        .filter(db.extract('year', Expense.date) == 2026,
                db.extract('month', Expense.date) == 5).scalar() or 0

    # Top category
    top_category = db.session.query(
        Expense.category,
        db.func.sum(Expense.amount).label('total')
    ).group_by(Expense.category)\
     .order_by(db.desc('total'))\
     .first()

    return monthly_total, top_category


# -------------------- APP SETUP --------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'yoursecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///C:/Users/varun/OneDrive/Desktop/Money Tracker/instance/moneytracker.db'

db.init_app(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# -------------------- AUTH ROUTES --------------------
@app.route("/register", methods=["GET", "POST"])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        hashed_pw = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        new_user = User(username=form.username.data, password=hashed_pw)
        db.session.add(new_user)
        db.session.commit()
        flash("Account created! Please log in.", "success")
        return redirect(url_for("login"))
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()

        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            user.is_active_session = True
            db.session.commit()
            flash("Login successful!", "success")
            return redirect(url_for("dashboard"))
        else:
            flash("Invalid credentials. Please try again.", "danger")

    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    current_user.is_active_session = False
    db.session.commit()
    logout_user()
    return redirect(url_for("login"))


# -------------------- DASHBOARD --------------------
@app.route("/dashboard")
@login_required
def dashboard():
    monthly_total, top_category = get_summary()
    return render_template("dashboard.html",
                           monthly_total=monthly_total,
                           top_category=top_category)


# -------------------- EXPENSE ROUTES --------------------
@app.route("/expenses", methods=["GET", "POST"])
@login_required
def expenses():
    form = ExpenseForm()
    if form.validate_on_submit():
        new_expense = Expense(
            user_id=current_user.id,
            category=form.category.data,
            amount=form.amount.data,
            date=form.date.data,
            description=form.description.data
        )
        db.session.add(new_expense)
        db.session.commit()
        flash("Expense added!", "success")
        return redirect(url_for("expenses"))

    # Always return something here
    all_expenses = Expense.query.filter_by(user_id=current_user.id).all()
    return render_template("expenses.html", form=form, expenses=all_expenses)


@app.route("/expense/<int:id>/edit", methods=["GET", "POST"])
@login_required
def edit_expense(id):
    expense = Expense.query.get_or_404(id)
    form = ExpenseForm(obj=expense)
    if form.validate_on_submit():
        expense.category = form.category.data
        expense.amount = form.amount.data
        expense.date = form.date.data
        expense.description = form.description.data
        db.session.commit()
        flash("Expense updated!", "success")
        return redirect(url_for("expenses"))
    return render_template("edit_expense.html", form=form)


@app.route("/expense/<int:id>/delete")
@login_required
def delete_expense(id):
    expense = Expense.query.get_or_404(id)
    db.session.delete(expense)
    db.session.commit()
    flash("Expense deleted!", "info")
    return redirect(url_for("expenses"))


@app.route("/active_users")
@login_required
def active_users():
    users = User.query.filter_by(is_active_session=True).all()
    return render_template("active_users.html", users=users)


# -------------------- REPORTS & EXPORT --------------------
@app.route("/reports", methods=["GET", "POST"])
@login_required
def reports():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    data = [{
        "date": e.date.strftime("%Y-%m-%d"),
        "category": e.category,
        "amount": e.amount
    } for e in expenses]

    df = pd.DataFrame(data)

    # Ensure static folder exists
    if not os.path.exists("static"):
        os.makedirs("static")

    pie_chart = None
    bar_chart = None
    category_summary = {}

    if not df.empty:
        # Category summary
        category_summary = df.groupby("category")["amount"].sum().to_dict()

        # Pie chart: category distribution
        plt.figure(figsize=(5,5))
        df.groupby("category")["amount"].sum().plot.pie(autopct='%1.1f%%')
        plt.title("Expenses by Category")
        plt.ylabel("")
        plt.savefig("static/reports_pie.png")
        plt.close()
        pie_chart = "static/reports_pie.png"

        # Bar graph: expenses over time
        plt.figure(figsize=(6,4))
        df.groupby("date")["amount"].sum().plot(kind="bar")
        plt.title("Expenses Over Time")
        plt.xlabel("Date")
        plt.ylabel("Amount")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig("static/reports_bar.png")
        plt.close()
        bar_chart = "static/reports_bar.png"

    return render_template("reports.html",
                           summary=category_summary,
                           pie_chart=pie_chart,
                           bar_chart=bar_chart)



@app.route("/export")
@login_required
def export():
    expenses = Expense.query.filter_by(user_id=current_user.id).all()
    data = [{
        "date": e.date,
        "category": e.category,
        "amount": e.amount,
        "description": e.description
    } for e in expenses]

    df = pd.DataFrame(data)

    # Ensure static folder exists
    if not os.path.exists("static"):
        os.makedirs("static")

    df.to_csv("static/expenses.csv", index=False)

    return redirect("/static/expenses.csv")


# -------------------- START SERVER --------------------
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
