import os
import json
from datetime import datetime, timedelta

TASKS_FILE = 'tasks.json'
DATE_FORMAT = '%Y-%m-%d'

class Task:
	def __init__(self, title, description, priority, due_date, completed=False):
		self.title = title
		self.description = description
		self.priority = int(priority)
		self.due_date = due_date  # string in YYYY-MM-DD
		self.completed = completed

	def to_dict(self):
		return {
			'title': self.title,
			'description': self.description,
			'priority': self.priority,
			'due_date': self.due_date,
			'completed': self.completed
		}

	@staticmethod
	def from_dict(data):
		return Task(
			data['title'],
			data['description'],
			data['priority'],
			data['due_date'],
			data.get('completed', False)
		)

	def __str__(self):
		status = '✓' if self.completed else '✗'
		overdue = ''
		if not self.completed and datetime.strptime(self.due_date, DATE_FORMAT) < datetime.now():
			overdue = ' [OVERDUE]'
		return f"[{status}] {self.title} (Priority: {self.priority}, Due: {self.due_date}{overdue})\n    {self.description}"

class TaskManager:
	def __init__(self):
		self.tasks = []
		self.load_tasks()

	def add_task(self, title, description, priority, due_date):
		self.tasks.append(Task(title, description, priority, due_date))
		self.save_tasks()

	def list_tasks(self):
		if not self.tasks:
			print("No tasks found.")
			return
		for idx, task in enumerate(self.tasks, 1):
			print(f"{idx}. {task}")

	def sort_tasks(self, by='due_date'):
		if by == 'due_date':
			self.tasks.sort(key=lambda t: (t.completed, t.due_date))
		elif by == 'priority':
			self.tasks.sort(key=lambda t: (t.completed, t.priority))

	def mark_complete(self, idx):
		if 0 <= idx < len(self.tasks):
			self.tasks[idx].completed = True
			self.save_tasks()
			print(f"Task '{self.tasks[idx].title}' marked as complete.")
		else:
			print("Invalid task number.")

	def summary(self):
		incomplete = [t for t in self.tasks if not t.completed]
		print(f"Incomplete tasks: {len(incomplete)}")
		upcoming = []
		now = datetime.now()
		soon = now + timedelta(days=3)
		for t in incomplete:
			due = datetime.strptime(t.due_date, DATE_FORMAT)
			if now <= due <= soon:
				upcoming.append(t)
		if upcoming:
			print("Upcoming deadlines (next 3 days):")
			for t in upcoming:
				print(f"- {t.title} (Due: {t.due_date})")
		else:
			print("No upcoming deadlines in the next 3 days.")

	def save_tasks(self):
		with open(TASKS_FILE, 'w') as f:
			json.dump([t.to_dict() for t in self.tasks], f, indent=2)

	def load_tasks(self):
		if os.path.exists(TASKS_FILE):
			with open(TASKS_FILE, 'r') as f:
				try:
					data = json.load(f)
					self.tasks = [Task.from_dict(d) for d in data]
				except Exception:
					self.tasks = []
		else:
			self.tasks = []

def input_date(prompt):
	while True:
		date_str = input(prompt)
		try:
			datetime.strptime(date_str, DATE_FORMAT)
			return date_str
		except ValueError:
			print(f"Invalid date format. Please use {DATE_FORMAT}.")

def input_priority(prompt):
	while True:
		val = input(prompt)
		if val.isdigit() and 1 <= int(val) <= 5:
			return int(val)
		print("Priority must be an integer between 1 and 5.")

def main():
	manager = TaskManager()
	while True:
		print("\nTask Scheduler Menu:")
		print("1. Add Task")
		print("2. List All Tasks")
		print("3. Sort Tasks by Due Date")
		print("4. Sort Tasks by Priority")
		print("5. Mark Task as Complete")
		print("6. View Summary")
		print("7. Exit")
		choice = input("Select an option (1-7): ").strip()
		if choice == '1':
			title = input("Title: ").strip()
			description = input("Description: ").strip()
			priority = input_priority("Priority (1-5): ")
			due_date = input_date("Due date (YYYY-MM-DD): ")
			manager.add_task(title, description, priority, due_date)
			print("Task added.")
		elif choice == '2':
			manager.list_tasks()
		elif choice == '3':
			manager.sort_tasks('due_date')
			print("Tasks sorted by due date.")
			manager.list_tasks()
		elif choice == '4':
			manager.sort_tasks('priority')
			print("Tasks sorted by priority.")
			manager.list_tasks()
		elif choice == '5':
			manager.list_tasks()
			idx = input("Enter task number to mark as complete: ")
			if idx.isdigit():
				manager.mark_complete(int(idx)-1)
			else:
				print("Invalid input.")
		elif choice == '6':
			manager.summary()
		elif choice == '7':
			manager.save_tasks()
			print("Goodbye!")
			break
		else:
			print("Invalid option. Please select 1-7.")

if __name__ == '__main__':
	main()
