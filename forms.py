from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import InputRequired, Length
from wtforms import FloatField, DateField, TextAreaField, SelectField

class RegisterForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=20)])
    submit = SubmitField("Register")

class LoginForm(FlaskForm):
    username = StringField("Username", validators=[InputRequired(), Length(min=4, max=20)])
    password = PasswordField("Password", validators=[InputRequired(), Length(min=6, max=20)])
    submit = SubmitField("Login")
    

class ExpenseForm(FlaskForm):
    category = SelectField("Category", choices=["Food", "Transport", "Shopping", "Bills", "Other"])
    amount = FloatField("Amount", validators=[InputRequired()])
    date = DateField("Date", validators=[InputRequired()])
    description = TextAreaField("Description")
    submit = SubmitField("Add Expense")

