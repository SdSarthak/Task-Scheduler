# Task Scheduler CLI - Advanced OOP Python Implementation

A comprehensive command-line task scheduler application that demonstrates advanced Object-Oriented Programming concepts in Python. This application provides a complete task management system with multiple priority categories, task types, and full CRUD operations.

## 🚀 Features

### Core Functionality
- **Add Tasks**: Create tasks with different priorities and types
- **Remove Tasks**: Delete tasks by ID or selection
- **Transfer Tasks**: Move tasks between priority categories
- **Complete Tasks**: Mark tasks as done with timestamp tracking
- **Search Tasks**: Find tasks by title or description
- **View Tasks**: Multiple filtering options (all, by priority, completed, pending)
- **Statistics**: Comprehensive task analytics and reporting

### Task Categories
1. **High Priority** - Urgent tasks with optional deadlines and escalation
2. **Low Priority** - Less urgent, general tasks
3. **To Do** - Standard tasks to be completed
4. **Prefer To Do** - Tasks you'd like to complete when possible
5. **Urgent** - Critical tasks requiring immediate attention
6. **Routine** - Recurring tasks with frequency settings
7. **Personal** - Personal life and self-care tasks
8. **Work** - Professional and work-related tasks

### Task Types
- **Regular Tasks**: Basic tasks with title, description, and priority
- **High Priority Tasks**: Include deadline management and escalation features
- **Routine Tasks**: Recurring tasks with frequency settings (daily, weekly, monthly)

## 🏗️ Object-Oriented Programming Concepts Demonstrated

### 1. Classes and Objects
- **Task**: Base class representing a general task
- **HighPriorityTask**: Specialized task class with deadline features
- **RoutineTask**: Specialized task class for recurring tasks
- **TaskManager**: Main orchestration class for task operations
- **TaskStorage**: Data persistence and file I/O operations
- **CLIInterface**: User interface and interaction handling

### 2. Inheritance
```python
# Example of inheritance hierarchy
TaskInterface (ABC)
    ↓
Task (Base Class)
    ↓
├── HighPriorityTask (Inherits from Task)
└── RoutineTask (Inherits from Task)
```

### 3. Polymorphism
- **Method Overriding**: Different task types implement `display()`, `to_dict()`, and `validate()` differently
- **Dynamic Method Dispatch**: Same method calls work across different task types
- **Interface Implementation**: All tasks implement the `TaskInterface` contract

### 4. Encapsulation
- **Private Attributes**: Using double underscore `__` for truly private members
- **Property Decorators**: Controlled access through getters and setters
- **Data Hiding**: Internal implementation details are hidden from external access

### 5. Abstraction
- **Abstract Base Class**: `TaskInterface` defines the contract for all tasks
- **Abstract Methods**: `display()`, `to_dict()`, `validate()` must be implemented by subclasses
- **Interface Segregation**: Clean separation of concerns

### 6. Composition and Aggregation
- **TaskManager HAS-A TaskStorage**: Composition relationship for data persistence
- **TaskManager HAS-A List of Tasks**: Aggregation relationship for task collection

### 7. Design Patterns
- **Factory Pattern**: `TaskFactory` creates appropriate task types based on priority
- **Strategy Pattern**: Different task types handle operations differently
- **Template Method**: Base task class provides template for common operations

## 📁 File Structure

```
Task Scheduler/
│
├── main.py          # Complete application implementation
├── README.md        # This documentation file
└── tasks.json       # Automatically created data storage file
```

## 🛠️ Installation and Setup

### Prerequisites
- Python 3.7 or higher
- No external dependencies required (uses only Python standard library)

### Running the Application
1. Clone or download the project files
2. Navigate to the project directory
3. Run the application:
   ```bash
   python main.py
   ```

## 💻 Usage Guide

### Starting the Application
When you run `main.py`, you'll see the main menu with the following options:

```
                MAIN MENU
==================================================
1.  Add New Task
2.  View All Tasks
3.  View Tasks by Priority
4.  View Completed Tasks
5.  View Pending Tasks
6.  Complete Task
7.  Remove Task
8.  Transfer Task Priority
9.  Search Tasks
10. View Statistics
11. Help
0.  Exit
==================================================
```

### Adding Tasks
1. Select option `1` from the main menu
2. Enter task title and description
3. Choose from 8 priority categories
4. For High Priority tasks: optionally set a deadline
5. For Routine tasks: specify frequency (daily/weekly/monthly)

### Managing Tasks
- **Complete**: Mark tasks as done with automatic timestamp
- **Remove**: Delete tasks with confirmation
- **Transfer**: Move tasks between priority categories
- **Search**: Find tasks by keywords in title or description

### Viewing Tasks
- **All Tasks**: See complete task list with details
- **By Priority**: Filter tasks by specific priority category
- **Completed/Pending**: View tasks by completion status
- **Statistics**: See analytics including completion rates and priority breakdown

## 🗃️ Data Storage

The application automatically saves all tasks to a `tasks.json` file using JSON serialization. The storage system:

- **Automatic Saving**: All changes are immediately persisted
- **Data Integrity**: Validation ensures only valid tasks are stored
- **Cross-Session Persistence**: Tasks remain available across application restarts
- **Human-Readable Format**: JSON format allows manual inspection if needed

## 🎯 Educational Value

This project serves as an excellent learning resource for:

### Beginner Concepts
- Basic class definition and object creation
- Method definition and calling
- Constructor usage with `__init__`
- Instance vs. class attributes

### Intermediate Concepts
- Inheritance and method overriding
- Property decorators for encapsulation
- Exception handling and validation
- File I/O and JSON serialization

### Advanced Concepts
- Abstract base classes and interfaces
- Polymorphism and dynamic dispatch
- Design patterns implementation
- Composition vs. inheritance decisions

## 🔧 Code Architecture

### Class Responsibilities

1. **TaskInterface (ABC)**
   - Defines the contract for all task types
   - Ensures consistent behavior across implementations

2. **Task (Base Class)**
   - Core task functionality and data management
   - Implements common behavior for all tasks
   - Provides foundation for specialized task types

3. **HighPriorityTask**
   - Extends Task with deadline management
   - Adds escalation functionality
   - Demonstrates inheritance and method overriding

4. **RoutineTask**
   - Extends Task with recurring task features
   - Manages frequency and next due dates
   - Shows specialization through inheritance

5. **TaskFactory**
   - Creates appropriate task objects based on priority
   - Implements the Factory design pattern
   - Encapsulates object creation logic

6. **TaskStorage**
   - Handles all file I/O operations
   - Manages data persistence and retrieval
   - Provides clean separation of storage concerns

7. **TaskManager**
   - Orchestrates all task operations
   - Implements business logic
   - Manages task collection and operations

8. **CLIInterface**
   - Handles user interaction and interface
   - Implements the view/controller layer
   - Manages application flow and user input

## 🚨 Error Handling

The application includes comprehensive error handling:

- **Input Validation**: All user inputs are validated before processing
- **File I/O Errors**: Graceful handling of storage issues
- **Data Integrity**: Validation ensures data consistency
- **User Feedback**: Clear error messages and recovery options

## 🔄 Extensibility

The architecture supports easy extension:

### Adding New Task Types
1. Create a new class inheriting from `Task`
2. Override necessary methods (`display()`, `to_dict()`, etc.)
3. Update `TaskFactory` to handle the new type
4. Add any specific UI handling in `CLIInterface`

### Adding New Features
- **Task Dependencies**: Could be added to the base Task class
- **Task Categories**: Additional categorization beyond priority
- **Reminders**: Time-based notification system
- **Task Templates**: Predefined task structures
- **Export/Import**: Additional data format support

## 📊 Sample Output

### Task Display Example
```
[task_1692000000000] Complete Project Documentation
Description: Write comprehensive documentation for the task scheduler
Priority: High Priority
Created: 2025-08-13 10:30:00
Status: ○ Pending
Deadline: 2025-08-15 17:00:00
```

### Statistics Example
```
              TASK STATISTICS
==================================================
Total Tasks: 15
Completed Tasks: 8
Pending Tasks: 7
Completion Rate: 53.3%

Tasks by Priority:
------------------------------
High Priority: 3
Low Priority: 2
To Do: 4
Prefer To Do: 1
Urgent: 2
Routine: 2
Personal: 1
Work: 0
```

## 🎓 Learning Objectives Achieved

By studying and running this application, you will understand:

1. **OOP Fundamentals**: Classes, objects, methods, and attributes
2. **Inheritance**: How to extend classes and override methods
3. **Polymorphism**: Same interface, different implementations
4. **Encapsulation**: Data hiding and controlled access
5. **Abstraction**: Interface definition and implementation
6. **Design Patterns**: Factory pattern and composition
7. **Error Handling**: Robust exception management
8. **File I/O**: Data persistence and serialization
9. **User Interface Design**: CLI application structure
10. **Code Organization**: Clean, maintainable code architecture

## 🤝 Contributing

This is an educational project designed to demonstrate OOP concepts. Feel free to:

- Study the code structure and implementation
- Modify and extend functionality for learning
- Use as a foundation for your own projects
- Share improvements and educational insights

## 📝 License

This project is created for educational purposes. Feel free to use, modify, and distribute for learning and educational activities.

## 🙋‍♂️ Support

If you have questions about the implementation or OOP concepts demonstrated:

1. Read through the extensive code comments
2. Use the built-in help system (option 11 in the menu)
3. Experiment with the code to see how changes affect behavior
4. Study the class hierarchy and method implementations

---

**Happy Learning! 🎉**

This Task Scheduler CLI demonstrates that Object-Oriented Programming is not just a theoretical concept but a practical approach to building maintainable, extensible, and well-organized software applications.
