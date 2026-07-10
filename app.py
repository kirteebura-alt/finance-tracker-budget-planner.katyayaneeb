import csv
from flask import Response
from flask import Flask, render_template, request, redirect, url_for
from extensions import db, login_manager
from models.budget import Budget
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from io import BytesIO
from flask import send_file
from datetime import datetime
from sqlalchemy import extract
from flask_login import (
    login_user,
    logout_user,
    login_required,
    current_user
)

app = Flask(__name__)
app.config.from_object("config.Config")

db.init_app(app)
login_manager.init_app(app)

login_manager.login_view = "login"

from models.user import User
from models.transaction import Transaction

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/")
def home():
    return render_template("home.html")


from flask import render_template, request, redirect, url_for, flash
from flask_login import login_user

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Password confirmation
        if password != confirm_password:
            flash("Passwords do not match.", "danger")
            return redirect(url_for("register"))

        # Username already exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "danger")
            return redirect(url_for("register"))

        # Email already exists
        if User.query.filter_by(email=email).first():
            flash("Email already registered.", "danger")
            return redirect(url_for("register"))

        # Create user
        user = User(
            username=username,
            email=email
        )

        user.set_password(password)

        db.session.add(user)
        db.session.commit()

        # Automatically log in the new user
        login_user(user)

        flash("Account created successfully!", "success")

        return redirect(url_for("dashboard"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("dashboard"))

        return "Invalid email or password"

    return render_template("login.html")


@app.route("/dashboard")
@login_required
def dashboard():

    transactions_query = Transaction.query.filter_by(
        user_id=current_user.id
    )

    category = request.args.get("category")

    if category:
        transactions_query = transactions_query.filter_by(
            category=category
        )

    transactions = transactions_query.all()

    total_income = sum(
        t.amount for t in transactions
        if t.transaction_type == "income"
    )

    total_expense = sum(
        t.amount for t in transactions
        if t.transaction_type == "expense"
    )

    balance = total_income - total_expense

    alerts = []

    budgets = Budget.query.filter_by(
        user_id=current_user.id
    ).all()

    for budget in budgets:

        category_expense = sum(
            t.amount
            for t in transactions
            if t.transaction_type == "expense"
            and t.category == budget.category
        )

        percentage = (
            category_expense / budget.monthly_limit
        ) * 100

        if percentage >= 80:
            alerts.append(
                f"You have used {percentage:.0f}% of your {budget.category} budget."
            )

    categories = db.session.query(
        Transaction.category
    ).filter_by(
        user_id=current_user.id
    ).distinct().all()

    categories = [c[0] for c in categories]

    total_transactions = len(transactions)

    total_budgets = len(budgets)

    recurring_transactions = sum(
        1 for t in transactions if t.is_recurring
    )

    return render_template(
        "dashboard.html",
        transactions=transactions,
        budgets=budgets,
        total_income=total_income,
        total_expense=total_expense,
        balance=balance,
        alerts=alerts,
        categories=categories,
        income = total_income,
        expense = total_expense,
        total_transactions=total_transactions,
        total_budgets=total_budgets,
        recurring_transactions=recurring_transactions
    )

@app.route("/add-transaction", methods=["GET", "POST"])
@login_required
def add_transaction():

    if request.method == "POST":

        amount = float(request.form["amount"])
        category = request.form["category"]
        transaction_type = request.form["transaction_type"]
        notes = request.form["notes"]
        is_recurring = "is_recurring" in request.form

        transaction = Transaction(
            user_id=current_user.id,
            amount=amount,
            category=category,
            transaction_type=transaction_type,
            notes=notes,
            is_recurring=is_recurring
        )

        db.session.add(transaction)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_transaction.html")

@app.route("/add-budget", methods=["GET", "POST"])
@login_required
def add_budget():

    if request.method == "POST":

        category = request.form["category"]
        monthly_limit = float(request.form["monthly_limit"])

        budget = Budget(
            user_id=current_user.id,
            category=category,
            monthly_limit=monthly_limit
        )

        db.session.add(budget)
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template("add_budget.html")

@app.route("/edit-transaction/<int:id>", methods=["GET", "POST"])
@login_required
def edit_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    if transaction.user_id != current_user.id:
        return "Unauthorized", 403

    if request.method == "POST":

        transaction.amount = float(request.form["amount"])
        transaction.category = request.form["category"]
        transaction.transaction_type = request.form["transaction_type"]
        transaction.notes = request.form["notes"]
        transaction.is_recurring = "is_recurring" in request.form
        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template(
        "edit_transaction.html",
        transaction=transaction
    )


@app.route("/delete-transaction/<int:id>")
@login_required
def delete_transaction(id):

    transaction = Transaction.query.get_or_404(id)

    if transaction.user_id != current_user.id:
        return "Unauthorized", 403

    db.session.delete(transaction)
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('home'))

with app.app_context():
    db.create_all()

@app.route("/edit-budget/<int:id>", methods=["GET", "POST"])
@login_required
def edit_budget(id):

    budget = Budget.query.get_or_404(id)

    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    if request.method == "POST":

        budget.category = request.form["category"]
        budget.monthly_limit = float(request.form["monthly_limit"])

        db.session.commit()

        return redirect(url_for("dashboard"))

    return render_template(
        "edit_budget.html",
        budget=budget
    )

@app.route("/delete-budget/<int:id>")
@login_required
def delete_budget(id):

    budget = Budget.query.get_or_404(id)

    if budget.user_id != current_user.id:
        return "Unauthorized", 403

    db.session.delete(budget)
    db.session.commit()

    return redirect(url_for("dashboard"))

@app.route("/charts")
@login_required
def charts():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    total_income = sum(
        t.amount for t in transactions
        if t.transaction_type == "income"
    )

    total_expense = sum(
        t.amount for t in transactions
        if t.transaction_type == "expense"
    )

    categories = {}

    for t in transactions:
        if t.transaction_type == "expense":

            if t.category not in categories:
                categories[t.category] = 0

            categories[t.category] += t.amount

    return render_template(
        "charts.html",
        income=total_income,
        expense=total_expense,
        labels=list(categories.keys()),
        values=list(categories.values())
    )

@app.route("/export-csv")
@login_required
def export_csv():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    def generate():

        data = [["Amount", "Category", "Type", "Notes"]]

        for t in transactions:
            data.append([
                t.amount,
                t.category,
                t.transaction_type,
                t.notes
            ])

        for row in data:
            yield ",".join(map(str, row)) + "\n"

    return Response(
        generate(),
        mimetype="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=transactions.csv"
        }
    )

@app.route("/export-pdf")
@login_required
def export_pdf():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    buffer = BytesIO()

    doc = SimpleDocTemplate(buffer)

    styles = getSampleStyleSheet()

    elements = []

    elements.append(
        Paragraph(
            "Personal Finance Report",
            styles["Title"]
        )
    )

    for t in transactions:
        elements.append(
            Paragraph(
                f"{t.category} - ₹{t.amount} - {t.transaction_type}",
                styles["BodyText"]
            )
        )

    doc.build(elements)

    buffer.seek(0)

    return send_file(
        buffer,
        as_attachment=True,
        download_name="finance_report.pdf",
        mimetype="application/pdf"
    )

@app.route("/prediction")
@login_required
def prediction():

    transactions = Transaction.query.filter_by(
        user_id=current_user.id
    ).all()

    income = sum(
        t.amount
        for t in transactions
        if t.transaction_type == "income"
    )

    expense = sum(
        t.amount
        for t in transactions
        if t.transaction_type == "expense"
    )

    predicted_expense = expense * 1.10

    predicted_balance = income - predicted_expense

    return render_template(
        "prediction.html",
        income=income,
        expense=expense,
        predicted_expense=predicted_expense,
        predicted_balance=predicted_balance
    )

@app.route('/assistant', methods=['GET', 'POST'])
@login_required
def assistant():

    response = ""

    if request.method == "POST":
        question = request.form.get("question", "").lower()

        if "save money" in question:
            response = "Try following the 50/30/20 rule."

        elif "budget" in question:
            response = "Create monthly spending limits."

        elif "investment" in question:
            response = "Start SIP investments for long-term growth."

        elif "expense" in question:
            response = "Track expenses daily to identify unnecessary spending."
        
        else:
            response = "I couldn't understand your question."

    return render_template(
        "assistant.html",
        response=response
    )


if __name__ == "__main__":
    app.run(debug=True)