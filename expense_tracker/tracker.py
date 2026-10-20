from typing import Optional
import json
import argparse
from pathlib import Path
from datetime import date, datetime


EXPENSES_FILE = Path(__file__).with_name("expenses.json")

def load_expenses() -> dict:
    empty = {"expenses": [], "budgets": {}}
    if not EXPENSES_FILE.exists():
        return empty.copy()
    try:
        with EXPENSES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return empty.copy()
    if not isinstance(data, dict):
        return empty.copy()
    data.setdefault("expenses", [])
    data.setdefault("budgets", {})
    if not isinstance(data["expenses"], list):
        data["expenses"] = []
    if not isinstance(data["budgets"], dict):
        data["budgets"] = {}
    return data


def add_expense(data: dict, description: str, amount: float, expense_date: Optional[str] = None, category: str = "General"):
    expenses_data = data.setdefault("expenses", [])
    expense_id = len(expenses_data) + 1
    expense_obj = {
        "id": str(expense_id),
        "date": (expense_date if expense_date is not None else date.today()).isoformat(),
        "description": description,
        "amount": amount,
        "category": category if category else "General"
    }
    year, month, day = str(expense_date).split("-")
    check_budget(data, f"{year}-{month}", amount)
    expenses_data.append(expense_obj)

    with EXPENSES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    print(f"Expense added successfully, ID: {expense_id}")



def update_expense(data: dict, expense_id: str, date: Optional[str], description: Optional[str], amount: Optional[float], category: Optional[str])-> list:
    expenses_data = data.setdefault("expenses", [])
    for expense in expenses_data:
        if expense.get("id") == expense_id:

            year, month, day = str(expense_date).split("-")
            check_budget(data, f"{year}-{month}", amount)

            if date.strip():
                expense["date"] = date
            if description.strip():
                expense["description"] = description
            if amount: 
                expense["amount"] = amount
            if category:
                expense["category"] = category
            break
        print("Expense updated sucessfully, ID: {expense_id}")
    
    return expenses_data

def delete_expense(expenses_data: list, expense_id: str):

    for i, expense in enumerate(expenses_data):
        if expense.get("id") == expense_id:
            expenses_data.pop(i)
            break
    return expenses_data
            
def list_expenses(expenses_data: list):
    print(f"{'# ID':<6}{'Date':<12}{'Description':<14}{'Amount':<15}{'Category'}")
    for expense in expenses_data:
        print(
            f"#{expense['id']:<5}"
            f"{expense['date']:<12}"
            f"{expense['description']:<14}"
            f"${expense['amount']:<15}"
            f"{expense.get('category', '')}"
        )


def summary_by_month(expenses_data: list, month: int, year: int | None = None) -> float:
    if year is None:
        year = date.today().year
    prefix = f"{year}-{month:02d}"  # e.g. "2024-08"
    total_by_filter = 0.0
    total = 0.0
    for expense in expenses_data:
        if expense["date"].startswith(prefix):
            total_by_filter += expense["amount"]
        total += expense["amount"]

    if month or year:
        return total_by_filter
    return total

def set_monthly_budget(expenses_data: dict, year: str | int, month: str | int, budget: float) -> dict:
    try:
        month_num = int(month)
        year_num = int(year)
    except (ValueError, TypeError):
        print("Invalid year or month")
        return expenses_data

    if month_num not in range(1, 13):
        print("Month must be between 1 and 12")
        return expenses_data

    key = f"{year_num}-{month_num:02d}"
    expenses_data.setdefault("budgets", {})[key] = budget

    with EXPENSES_FILE.open("w", encoding="utf-8") as f:
        json.dump(expenses_data, f, indent=2)

    print(f"Budget set for {key}: ${budget}")
    return expenses_data


def check_budget(data, month_str: str, amount) -> float:

    """
    month = "2026-02"
    """

    expenses = data.get("expenses", [])
    budgets = data.get("budgets", {})

    year, month = month_str.split("-")
    max_budget = budgets.get(f"{year}-{month}", -1)
   
    if max_budget == -1:
        print("No budget set for this month. Add anything, be free! "
                "Or set a monthly buget and be responsible \n")
        return

    sum_expenses = summary_by_month(expenses, year, month)

    if sum_expenses >= max_budget: 
        raise ValueError("Unable to add mount, the budget has already been met. No more expenses allowed for the month.")

    if sum_expenses + amount > max_budget:
        difference = max_budget - sum_expenses
        raise ValueError("Unable to add amount, this will exceed the max budget for the month"
                        f"Add an amount less than or equal to {difference}")




def main():
    parser = argparse.ArgumentParser(prog="expense-tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("--description", required=True)
    add.add_argument("--amount", type=float, required=True)
    add.add_argument("--date", type=str)
    add.add_argument("--category")

    sub.add_parser("list")

    delete = sub.add_parser("delete")
    delete.add_argument("--id", required=True)

    summary = sub.add_parser("summary")
    summary.add_argument("--month", type=int)

    update = sub.add_parser("update")
    update.add_argument("--id", required=True)
    update.add_argument("--date", type=date)
    update.add_argument("--description")
    update.add_argument("--amount", type=float)
    update.add_argument("--category")


    args = parser.parse_args()
    data = load_expenses()

    if args.command == "add":
        expense_date = (
            date.fromisoformat(args.date) if args.date else None
        )
        add_expense(data, args.description, args.amount, expense_date, args.category)
    if args.command == "update":
        update_expense(data, args.id, args.date, args.description, args.amount, args.category)
    elif args.command == "list":
        list_expenses(data["expenses"])
    elif args.command == "delete":
        delete_expense(data["expenses"], args.id)
    elif args.command == "summary":
        expenses = data["expenses"]
        total = summary_by_month(expenses, args.month) if args.month else summary_by_month(expenses, 0)
        print(f"Total expenses: ${total}")

if __name__ == "__main__":
    main()