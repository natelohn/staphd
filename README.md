# Staph-D — Staff Scheduling App

Staph-D is a web app for building and managing staff schedules. It lets you create schedules, assign shifts to staff members (called "Staphers"), track qualifications, and export finished schedules to Excel.

---

## Contents

- [Before You Begin](#before-you-begin)
- [One-Time Setup](#one-time-setup)
- [Running the App](#running-the-app)
- [Stopping the App](#stopping-the-app)
- [Troubleshooting](#troubleshooting)

---

## Before You Begin

You will need the following tools installed on your Mac before setting up Staph-D. If you have already done this, skip to [One-Time Setup](#one-time-setup).

### 1. Homebrew

Homebrew is a package manager for Mac that makes installing everything else easy.

Open **Terminal** (press `Command + Space`, type "Terminal", press Enter) and run:

```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the on-screen prompts. When it finishes, close and reopen Terminal.

### 2. Python 3

```
brew install python@3.11
```

Verify it worked:

```
python3 --version
```

You should see something like `Python 3.11.x`.

### 3. PostgreSQL (the database)

```
brew install postgresql@14
brew services start postgresql@14
```

Verify it is running:

```
pg_isready
```

You should see: `localhost:5432 - accepting connections`

---

## One-Time Setup

Do these steps **once** when you first install Staph-D.

### Step 1 — Get the code

If you received a zip file, unzip it and note the folder path. If you are cloning from GitHub:

```
git clone <repository-url>
cd staphd
```

Open Terminal and navigate into the staphd folder:

```
cd /path/to/staphd
```

> **Tip:** You can drag the folder from Finder into the Terminal window and it will type the path for you.

### Step 2 — Create a virtual environment

A virtual environment keeps Staph-D's dependencies separate from the rest of your computer.

```
python3 -m venv venv
source venv/bin/activate
```

Your terminal prompt will change to show `(venv)` at the beginning — that means it worked.

> You will need to run `source venv/bin/activate` each time you open a new Terminal window before running the app. The `make run` command handles this automatically if you are already in the folder.

### Step 3 — Install dependencies

```
pip install -r requirements.txt
```

This installs everything Staph-D needs. It may take a minute or two.

### Step 4 — Create the database

```
createdb staphddb
```

### Step 5 — Set up the database tables

```
make setup
```

This will run through some setup steps and then ask you to create an admin account. Choose a username and password you will remember — this is how you will log in.

---

## Running the App

Every time you want to use Staph-D, open Terminal, navigate to the staphd folder, activate the virtual environment, and run:

```
make run
```

Then open your browser and go to:

```
http://localhost:8000
```

Log in with the admin account you created during setup.

> **Shortcut for next time:** Once you have done the one-time setup, the only things you need each session are:
> 1. Open Terminal in the staphd folder
> 2. `source venv/bin/activate`
> 3. `make run`

---

## Stopping the App

Press `Control + C` in the Terminal window where the app is running. The server will stop.

---

## Troubleshooting

**"make: command not found"**
Run `xcode-select --install` in Terminal and try again.

**"connection refused" or database errors**
PostgreSQL may not be running. Start it with:
```
brew services start postgresql@14
```

**"No module named ..." errors**
Make sure your virtual environment is active. You should see `(venv)` in your terminal prompt. If not:
```
source venv/bin/activate
```

**The page shows an error after logging in**
Run `python manage.py migrate` to make sure the database is up to date, then try `make run` again.

**Port 8000 is already in use**
Another process is using that port. Run:
```
lsof -i :8000
```
Find the PID number in the output, then run `kill <PID>`. Then try `make run` again.
