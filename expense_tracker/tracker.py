from typing import Optional
import json
import csv
import argparse
import calendar
from pathlib import Path
from datetime import date


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


def save_data(data: dict) -> None:
    with EXPENSES_FILE.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def next_expense_id(expenses_data: list) -> str:
    if not expenses_data:
        return "1"
    ids = [int(e["id"]) for e in expenses_data if str(e.get("id", "")).isdigit()]
    return str(max(ids, default=0) + 1)


def resolve_date(expense_date: Optional[date | str] = None) -> str:
    if expense_date is None:
        return date.today().isoformat()
    if isinstance(expense_date, date):
        return expense_date.isoformat()
    return date.fromisoformat(str(expense_date)).isoformat()


def find_expense(expenses_data: list, expense_id: str) -> dict | None:
    for expense in expenses_data:
        if str(expense.get("id")) == str(expense_id):
            return expense
    return None


def add_expense(
    data: dict,
    description: str,
    amount: float,
    expense_date: Optional[date | str] = None,
    category: str = "General",
):
    if amount < 0:
        raise ValueError("Amount cannot be negative")

    expenses_data = data.setdefault("expenses", [])
    date_str = resolve_date(expense_date)
    year_month = date_str[:7]
    check_budget(data, year_month, amount)

    expense_id = next_expense_id(expenses_data)
    expense_obj = {
        "id": expense_id,
        "date": date_str,
        "description": description,
        "amount": amount,
        "category": category if category else "General",
    }
    expenses_data.append(expense_obj)
    save_data(data)
    print(f"Expense added successfully (ID: {expense_id})")


def update_expense(
    data: dict,
    expense_id: str,
    expense_date: Optional[date | str] = None,
    description: Optional[str] = None,
    amount: Optional[float] = None,
    category: Optional[str] = None,
) -> dict:
    expenses_data = data.setdefault("expenses", [])
    expense = find_expense(expenses_data, expense_id)
    if expense is None:
        raise ValueError(f"Expense with ID {expense_id} not found")

    if amount is not None and amount < 0:
        raise ValueError("Amount cannot be negative")

    new_date = resolve_date(expense_date) if expense_date is not None else expense["date"]
    new_amount = amount if amount is not None else expense["amount"]
    delta = new_amount - expense["amount"]
    if delta > 0:
        check_budget(data, new_date[:7], delta)

    if expense_date is not None:
        expense["date"] = new_date
    if description is not None and description.strip():
        expense["description"] = description
    if amount is not None:
        expense["amount"] = amount
    if category is not None and category.strip():
        expense["category"] = category

    save_data(data)
    print(f"Expense updated successfully (ID: {expense_id})")
    return data


def delete_expense(data: dict, expense_id: str) -> dict:
    expenses_data = data.setdefault("expenses", [])
    for i, expense in enumerate(expenses_data):
        if str(expense.get("id")) == str(expense_id):
            expenses_data.pop(i)
            save_data(data)
            print(f"Expense deleted successfully (ID: {expense_id})")
            return data
    raise ValueError(f"Expense with ID {expense_id} not found")


def list_expenses(expenses_data: list, category: Optional[str] = None):
    rows = expenses_data
    if category:
        rows = [e for e in expenses_data if e.get("category", "").lower() == category.lower()]

    print(f"{'# ID':<6}{'Date':<12}{'Description':<14}{'Amount':<15}{'Category'}")
    for expense in rows:
        print(
            f"#{expense['id']:<5}"
            f"{expense['date']:<12}"
            f"{expense['description']:<14}"
            f"${expense['amount']:<15}"
            f"{expense.get('category', '')}"
        )


def summary_by_month(
    expenses_data: list,
    month: int | str | None = None,
    year: int | str | None = None,
) -> float:
    if month is None or int(month) == 0:
        return sum(expense["amount"] for expense in expenses_data)

    month_num = int(month)
    year_num = int(year) if year is not None else date.today().year
    prefix = f"{year_num}-{month_num:02d}"
    return sum(
        expense["amount"]
        for expense in expenses_data
        if expense["date"].startswith(prefix)
    )


def set_monthly_budget(
    expenses_data: dict, year: str | int, month: str | int, budget: float
) -> dict:
    try:
        month_num = int(month)
        year_num = int(year)
    except (ValueError, TypeError):
        print("Invalid year or month")
        return expenses_data

    if month_num not in range(1, 13):
        print("Month must be between 1 and 12")
        return expenses_data

    if budget < 0:
        raise ValueError("Budget cannot be negative")

    key = f"{year_num}-{month_num:02d}"
    expenses_data.setdefault("budgets", {})[key] = budget
    save_data(expenses_data)
    print(f"Budget set for {key}: ${budget}")
    return expenses_data


def check_budget(data, month_str: str, amount) -> None:
    """
    month_str = "2026-02"
    """
    expenses = data.get("expenses", [])
    budgets = data.get("budgets", {})

    year, month = month_str.split("-")
    max_budget = budgets.get(f"{year}-{month}", -1)

    if max_budget == -1:
        print(
            "No budget set for this month. Add anything, be free! "
            "Or set a monthly budget and be responsible \n"
        )
        return

    sum_expenses = summary_by_month(expenses, month, year)

    if sum_expenses >= max_budget:
        raise ValueError(
            "Unable to add amount, the budget has already been met. "
            "No more expenses allowed for the month."
        )

    if sum_expenses + amount > max_budget:
        difference = max_budget - sum_expenses
        raise ValueError(
            "Unable to add amount, this will exceed the max budget for the month. "
            f"Add an amount less than or equal to ${difference}"
        )


def export_expenses(expenses_data: list, output_path: str | Path) -> None:
    path = Path(output_path)
    fieldnames = ["id", "date", "description", "amount", "category"]
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for expense in expenses_data:
            writer.writerow(expense)
    print(f"Expenses exported to {path}")


def main():
    parser = argparse.ArgumentParser(prog="expense-tracker")
    sub = parser.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add")
    add.add_argument("--description", required=True)
    add.add_argument("--amount", type=float, required=True)
    add.add_argument("--date", type=str)
    add.add_argument("--category")

    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--category")

    delete = sub.add_parser("delete")
    delete.add_argument("--id", required=True)

    summary = sub.add_parser("summary")
    summary.add_argument("--month", type=int)
    summary.add_argument("--year", type=int)

    update = sub.add_parser("update")
    update.add_argument("--id", required=True)
    update.add_argument("--date", type=str)
    update.add_argument("--description")
    update.add_argument("--amount", type=float)
    update.add_argument("--category")

    budget = sub.add_parser("set_budget")
    budget.add_argument("--year", required=True)
    budget.add_argument("--month", required=True)
    budget.add_argument("--max", type=float, required=True)

    export = sub.add_parser("export")
    export.add_argument("--output", default="expenses.csv")

    args = parser.parse_args()
    data = load_expenses()

    try:
        if args.command == "add":
            expense_date = date.fromisoformat(args.date) if args.date else None
            add_expense(data, args.description, args.amount, expense_date, args.category)
        elif args.command == "update":
            update_expense(
                data, args.id, args.date, args.description, args.amount, args.category
            )
        elif args.command == "list":
            list_expenses(data["expenses"], args.category)
        elif args.command == "delete":
            delete_expense(data, args.id)
        elif args.command == "summary":
            expenses = data["expenses"]
            total = summary_by_month(expenses, args.month, args.year)
            if args.month:
                month_name = calendar.month_name[args.month]
                print(f"Total expenses for {month_name}: ${total}")
            else:
                print(f"Total expenses: ${total}")
        elif args.command == "set_budget":
            set_monthly_budget(data, args.year, args.month, args.max)
        elif args.command == "export":
            export_expenses(data["expenses"], args.output)
    except ValueError as err:
        print(err)


if __name__ == "__main__":
    main()
