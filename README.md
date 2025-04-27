## 📚 Quiz Master

### **Author**

**Isha Saini**  
📧 Email: 22f3002890@ds.study.iitm.ac.in

### **Project Overview**

**Quiz Master** is a multi-user exam preparation platform designed to help students practice quizzes based on different subjects and chapters. The platform supports role-based access for **users** and **administrators**, quiz management, scoring, and analytical insights through summary charts.

---

## 🚀 **Technologies Used**

- **Backend:** Python, Flask, Flask-SQLAlchemy
- **Frontend:** Jinja2 Templates, Bootstrap
- **Database:** SQLite
- **Data Visualization:** Chart.js

---

## 🛄 **Database Schema**

The database consists of the following entities:

1. **User**

   - Stores user details and authentication info
   - **Fields:** `id`, `username`, `passhash`, `fullName`, `email`, `is_admin`
   - **Relationships:** One-to-Many with **Scores**

2. **Subject**

   - Represents different subjects
   - **Fields:** `id`, `name`, `description`
   - **Relationships:** One-to-Many with **Chapters**

3. **Chapter**

   - Represents chapters within a subject
   - **Fields:** `id`, `subject_id`, `name`, `description`
   - **Relationships:** One-to-Many with **Quizzes**

4. **Quiz**

   - A quiz under a specific chapter
   - **Fields:** `id`, `chapter_id`, `date_of_quiz`, `time_duration`, `remarks`
   - **Relationships:** One-to-Many with **Questions** and **Scores**

5. **Question**

   - Represents a question in a quiz
   - **Fields:** `id`, `quiz_id`, `question_heading`, `question_statement`, `option1`, `option2`, `option3`, `option4`, `correct_option`

6. **Score**
   - Stores user quiz attempts and scores
   - **Fields:** `id`, `quiz_id`, `user_id`, `time_stamp_of_attempt`, `total_scored`

---

## 🛠 **Architecture Design**

The project follows the **Model-View-Controller (MVC)** architecture:

- **Controllers**: Handles route logic for Home, Admin, and User functionalities.
- **Templates**: Contains Jinja2-based HTML templates organized into subfolders.
- **Models**: Defines database models as per the schema.
- **Instance**: Stores the SQLite database file.
- **Application**: Manages configuration files and project settings.

---

## 🔥 **Main Features**

### 🔹 **Admin Controls**

👉 Manage subjects, chapters, quizzes, and users.  
👉 View detailed analytics through **summary charts**.  
👉 Monitor quiz participation and **user performance**.

### 🔹 **User Features**

👉 Register and log in to **attempt quizzes**.  
👉 View **past quiz scores** and performance history.  
👉 Edit **profile details** and update passwords.  
👉 **Summary charts** to track quiz performance and statistics.

---

## ⚡ **Installation & Setup**

### **1️⃣ Clone the Repository**

```sh
git clone https://github.com/your-repository/quiz-master.git
cd quiz-master
```

### **2️⃣ Set Up Virtual Environment**

```sh
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### **3️⃣ Install Dependencies**

```sh
pip install -r requirements.txt
```

### **4️⃣ Run the Application**

```sh
flask run
```

