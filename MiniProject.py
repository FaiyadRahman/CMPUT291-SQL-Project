import sqlite3
import datetime
import time
import sys
import os.path
import getpass

PAGE_INCREMENT = 5

class App:
    # intializing varables
    connection = None
    cursor = None
    session_id = None
    Cid = None
    session_start = 0
    Name = ""

    MoviesWatching = list()
    MovieTimes = dict()
    
    def connect(self,File):
        # establish connection with a database
        Current_Dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(Current_Dir, File)
        self.connection = sqlite3.connect(db_path)
        self.cursor = self.connection.cursor()
        return
        return

    def customer_page(self):
        print()
        print("Welcome,",self.Name)
        print("CUSTOMER MENU \n")

        # choose which function the user wants
        Option = input("Do you wish to start a session (ST), search for a movie (SE), end watching a movie (EM), end a session (ES), logout (L), or exit the program(E)? ")
        if Option.lower() == 'l':
            self.start()
            return
        elif Option.lower() == 'st':
            #start session
            self.start_session()
            print("Session  Started")
        elif Option.lower() == 'se':
            #search for movies
            self.search_movies()
        elif Option.lower() == 'em':
            #end watching a movie
            self.end_movie()
        elif Option.lower() == 'es':
            #end a session
            print('Ended current session')
            self.end_session()
        elif Option.lower() == 'e':
            exit()
        else:
            print('invalid input please try again')
            self.customer_page()

    def search_movies(self):
        # check if there is an active session
        if self.session_id == None:
            print("Please start a session first")
            self.customer_page()
            return
        else:
            # create a tuple with all valid keywords
            Keyword = ""
            KeywordList = ()
            while (Keyword.lower() != "//exit//"):
                Keyword = input("Please input a keyword or '//EXIT//' to end the program: ").strip()
                if (Keyword.lower() != "//exit//"):
                    if (len(Keyword) == 0):
                        print("Empty keywords are invalid")
                    else:
                        KeywordList= KeywordList + (Keyword,)
            if len(KeywordList) > 0:
                # combine the keywords into a single query 
                Query = ""
                for i in range(len(KeywordList)):
                    if (i != len(KeywordList)-1 and len(KeywordList) != 1):
                        Query += '''SELECT ? as "word" UNION '''
                    else:
                        Query += '''SELECT ? as "word"'''
                # return movie title, year, runtime, mid if the keyword matches
                # movie title, role, moviePerson name
                # ranked by number of keyword matches
                self.cursor.execute('''SELECT m.title, m.year, m.runtime, m.mid
                    FROM movies m, casts c, moviePeople mp, ({}) as "k"
                    WHERE c.pid = mp.pid AND m.mid = c.mid
                    AND LOWER(m.title || c.role || mp.name) LIKE '%' || LOWER(k.word) || '%'
                    GROUP by m.mid
                    ORDER by COUNT(DISTINCT k.word) DESC'''.format(Query),KeywordList)
                Results = self.cursor.fetchall()
                Choice = 'n'
                Page = 0
                self.Display_results(Results,Page)

                # display the next 5 results
                while Choice.lower() == 'n':
                    Choice = input("Do you want to see the next 5 movies (N), see more information about the movie (M), or return to homepage (E)? ")
                    if (Choice.lower() == 'n'):
                        Page += PAGE_INCREMENT
                        self.Display_results(Results,Page)
                # return to customer page
                if Choice.lower() == 'e':
                    self.customer_page()
                    return
                elif Choice.lower() == 'm':
                    # get more info about the selected movie
                    Choice = input("Select a movie #: ")
                    if (not Choice.isnumeric()) or (Choice.isnumeric() and int(Choice) >= len(Results)):
                        print("Invalid Input, returning to homepage")
                        self.customer_page()
                        return
                    self.MovieInfo(Results[int(Choice)][3])
                    return
                else:
                    print("Invalid option, redirecting to homepage")
                    self.customer_page()
                    return
            else:
                print("No keywords inputted, please try again.")
                self.search_movies()
                return

    def MovieInfo(self,movieId):
        # find the number of people who has watched this movie
        self.cursor.execute('''SELECT COUNT(DISTINCT w.cid)
            FROM movies m, watch w
            WHERE w.mid = m.mid
            AND w.duration * 2 >= m.runtime
            AND m.mid = ?
            GROUP by m.mid''',(movieId,))
        Count = self.cursor.fetchone()
        print("Number of Customers who watched this movie:",Count == None and '0' or Count[0])
        # find all moviePeople who have roles in the movie
        self.cursor.execute('''SELECT mp.name, mp.pid
            FROM movies m, casts c, moviePeople mp
            WHERE c.mid = m.mid
            AND m.mid = ?
            AND mp.pid = c.pid''',(movieId,))
        Results = self.cursor.fetchall()
        # number the moviePeople
        for i in range(len(Results)):
            print("#" + str(i) + ". "+ Results[i][0])
        Choice = input("Input 'W' to watch a movie, the # of a cast member to follow them, or 'E' to return to the homepage. ")
        if Choice.lower() == "w":
            #  check if the a movie is already being watched in the current section
            Found = len(self.MoviesWatching)

            if Found > 0:
                print("Already watching movie! ")
                self.customer_page()
                return
            else:
                # start watching a movie
                self.MoviesWatching.append(movieId)
                self.MovieTimes[movieId] = time.time()
                self.cursor.execute('''INSERT INTO watch VALUES(?,?,?,NULL);''',(self.session_id,self.Cid,movieId))
                self.connection.commit()
                print('starting movie')
                self.customer_page()
                return
        elif Choice.lower() == "e":
            self.Cid = None
            self.customer_page()
            return
        else:
            if (not Choice.isnumeric()) or (Choice.isnumeric() and int(Choice) >= len(Results)):
                print("Invalid Input, returning to homepage")
                self.customer_page()
                return
            #  check if the user is already following the movieperson
            self.cursor.execute('''SELECT *
                FROM follows f
                WHERE f.cid = ? AND f.pid = ?''',(self.Cid,Results[int(Choice)][1]))
            Found = self.cursor.fetchone()
            if Found:
                # already following redirect back to home
                print("Already following!")
                self.customer_page()
                return
            else:
                if (not Choice.isnumeric()) or (Choice.isnumeric() and int(Choice) >= len(Results)):
                    print("Invalid Input, returning to homepage")
                    self.customer_page()
                    return
                # create the following row and add it to follow table
                self.cursor.execute('''INSERT INTO follows VALUES(?,?);''',(self.Cid,Results[int(Choice)][1]))
                self.connection.commit()
                self.customer_page()
                return


    def Display_results(self,results,page):
        # print the next 5 pages
        Maxed = min(page+PAGE_INCREMENT,len(results))
        for i in range(page,Maxed):
            print("#" + str(i) + ". Title: " + str(results[i][0]) + " Year: " + str(results[i][1]) + " Runtime: " + str(results[i][2]))
        
    def start_session(self):
        # start a new session if one doesn't exist
        if self.session_id == None:
            print("Starting Session.")
            # assign a unique session id which is the current number of rows in sessions table + 1
            self.cursor.execute('''SELECT COUNT(*) FROM sessions;''')
            Result = self.cursor.fetchone()
            self.session_id = Result[0] + 1
            # get the current date and time
            self.session_start = time.time()
            # insert values into sessions table
            self.cursor.execute('''INSERT INTO sessions VALUES(?,?,?,NULL);''',(self.session_id,self.Cid,datetime.datetime.now()))
            self.connection.commit()
        else:
            print("Please end your current session before starting a new one")
        self.customer_page()


    def end_movie(self):
        # check if there is an active session
        if self.session_id != None:
            # find list of movies that the user is watching in the current session
            if len(self.MoviesWatching) > 0:
                self.cursor.execute('''  
                SELECT m.title, w.mid, w.duration, m.runtime
                FROM watch w, movies m
                WHERE w.cid = :Cid AND w.sid = :session_id AND w.mid = m.mid AND w.duration IS NULL
                ''',{"session_id":self.session_id, "Cid":self.Cid})
                results = self.cursor.fetchall()
                
                # display the numbered list
                for i,result in enumerate(results):
                    print("#" + str(i),"Movie: " + result[0])
                
                # get valid input
                num = input('Select movie number to end ')
                if (not num.isnumeric() or (num.isnumeric() and int(num) >= len(results))):
                    print("Invalid input, try again")
                    self.end_movie()
                    return
                num = int(num)

                # gather relevant information of the user's choice
                mid = results[num][1]
                duration = results[num][2]
                runtime = results[num][3]
                
                # calculate the time passed from the beginning of the session to the current time in minutes
                time_passed = (time.time() - self.MovieTimes[mid])//60
                
                # calculate the time watched for a movie
                if duration == None:
                    if time_passed > runtime:
                        time_passed = runtime
                else:
                    if time_passed + duration > runtime:
                        time_passed = runtime
                    else:
                        time_passed += duration

                # update the watch table with the updated duration
                self.cursor.execute('''
                UPDATE watch
                SET duration = ?
                WHERE cid = ? AND sid = ? AND mid = ?
                ''',(time_passed, self.Cid, self.session_id, mid))
                self.MoviesWatching.remove(mid)
                self.customer_page()
            else:
                print('No movies to end')
                self.customer_page()
        else:
            print('No active session')
            self.customer_page()

        self.connection.commit()

    def end_session(self):
        # check if there is an active session
        if self.session_id != None:
            print("Ending session")
            # find list of movies that the user is watching in the current session
            self.cursor.execute('''  
            SELECT m.title, w.mid, w.duration, m.runtime
            FROM watch w, movies m
            WHERE w.cid = :Cid AND w.sid = :session_id AND w.mid = m.mid AND w.duration IS NULL
            ''',{"session_id":self.session_id, "Cid":self.Cid})
            results = self.cursor.fetchall()
        
            # calculate time passed from the start of the session to the current time
            Session_time_passed = ((time.time() - self.session_start))//60

            # for each movie being watched, update its duration
            for result in results:
                # gather relevant information of the user's choice
                mid = result[1]
                duration = result[2]
                runtime = result[3]
                time_passed_temp = ((time.time() - self.MovieTimes[mid]))//60

                # calculate duration for each movie
                if duration == None:
                    if time_passed_temp > runtime:
                        time_passed_temp = runtime
                else:
                    if time_passed_temp + duration > runtime:
                        time_passed_temp = runtime
                    else:
                        time_passed_temp += duration

                # update watched table with updated duration
                self.cursor.execute('''
                UPDATE watch
                SET duration = ?
                WHERE cid = ? AND sid = ? AND mid = ?
                ''',(time_passed_temp, self.Cid, self.session_id, mid))
                self.MoviesWatching.remove(mid)
                
                self.connection.commit()
            # update sessions table with duration of session
            self.cursor.execute('''
                UPDATE sessions
                SET duration = ?
                WHERE sid = ? AND cid = ?
            ''',(Session_time_passed, self.session_id, self.Cid))
            self.connection.commit()
            
            # clear session_id to close the current session
            self.session_id = None
            self.customer_page()
            return
        else:
            print("No session to end, please start a session first")
            self.customer_page()
            return

    def editor_page(self):
        print("EDITOR MENU\n")

        # select option based on user input
        Option = input("Do you wish to add a movie, update a recommendation, logout, or exit the program(M,R,L,E): ")
        if Option.lower() == 'l':
            # login
            self.start()
        elif Option.lower() == 'r':
            # update a recommendation
            self.recommended_page()
        elif Option.lower() == 'm':
            # add a movie
            self.add_movie()
        elif Option.lower() == 'e':
            print('Exiting')
            exit()
        else:
            print('Invalid input please try again')
            self.editor_page()

    def recommended_page(self):
        Id = input("Select 'M' for monthly, 'A' for annual, 'AT' for all-time, or 'E' to cancel: ")
        Times = {"m": '-1 months', "a": '-1 years', 'at': '-100 years'}
        Modes = {"m": 0, "a": 0, 'at': 1}
        if Id.lower() == 'e':
            self.editor_page()
            return
        elif Id.lower() in ['m', 'a', 'at']:
            # Processes all the data for the recommendations, all pairs are unique
            self.cursor.execute('''SELECT a.m1, a.m2, a.num, CASE when r.score IS NULL THEN "No" ELSE "Yes" END as "InDB", IFNULL(r.score,"N/A")
                FROM
                (SELECT w1.mid as m1, w2.mid as m2, COUNT(DISTINCT w1.cid) as num
                FROM watch w1, watch w2, sessions s1, sessions s2, movies m1, movies m2
                WHERE w1.cid = w2.cid AND m1.mid = w1.mid AND m2.mid = w2.mid
                AND w1.duration * 2 >= m1.runtime AND w2.duration * 2 >= m2.runtime
                AND w1.sid = s1.sid AND w2.sid = s2.sid AND w1.mid < w2.mid
                AND ((s1.sdate >= DATETIME('now' , :time) AND s2.sdate >= DATETIME('now' , :time)) OR (:mode = 1))
                GROUP by w1.mid, w2.mid
                ORDER by COUNT(DISTINCT w1.cid) DESC) as a
                LEFT OUTER JOIN recommendations r 
                ON (r.watched = a.m1 AND r.recommended = a.m2) OR (r.watched = a.m2 AND r.recommended = a.m1);''',{"time":Times[Id.lower()], "mode":Modes[Id.lower()]})
            Results = self.cursor.fetchall()

            # Outputs a list of all the pair details
            for i in range(len(Results)):
                print("#" + str(i) + " Movie ID:",Results[i][0],"Movie ID:",Results[i][1],"Distinct Watch Count:",Results[i][2],"In Database?:",Results[i][3],"Score:",Results[i][4])
            print()
            
            if len(Results) != 0:
                # User inputs their choices for processing the recommendations
                Id = input("Select 'D' to delete, 'A' to add, 'U' to update the score, or 'E' to cancel: ")
                if Id.lower() == 'e':
                    self.editor_page()
                    return
                elif Id.lower() == 'd':
                    Num = input("Select a movie pair #: ")

                    # Checks for numeric input
                    if (not Num.isnumeric() or (Num.isnumeric() and int(Num) >= len(Results))):
                        print("Invalid Input, returning to homepage")
                        self.editor_page()
                        return
                    Num = int(Num)

                    if Results[int(Num)][3] == "Yes":

                        # Deletes the movie if it exists
                        self.cursor.execute('''DELETE FROM recommendations
                            WHERE (watched = :m1 AND recommended = :m2) OR (watched = :m2 AND recommended = :m1);''',{"m1":Results[int(Num)][0],"m2":Results[int(Num)][1]})
                        self.connection.commit()
                        self.editor_page()
                        return
                    else:
                        print("Invalid ID, returning to Homepage")
                        self.editor_page()
                        return
                elif Id.lower() == 'a':
                    # Choice for adding movies triggered
                    Num = input("Select a movie pair #: ")

                    if (not Num.isnumeric() or (Num.isnumeric() and int(Num) >= len(Results))):
                        print("Invalid Input, returning to homepage")
                        self.editor_page()
                        return

                    # Below checks whether the input can be converted into a floating point
                    # If not, the input is invalid
                    Score = 0
                    try:
                        Score = float(input("Input a score: "))
                    except:
                        print("Numeric score expected, returning to homepage")
                        self.editor_page()
                        return

                    
                    if Results[int(Num)][3] == "No":
                        # There are no recommendations currently, insert into the database
                        self.cursor.execute('''INSERT INTO recommendations VALUES(?,?,?);''',(Results[int(Num)][0],Results[int(Num)][1],Score))
                        self.connection.commit()
                        self.editor_page()
                        return
                    else:
                        # There already exists a recommendation
                        print("Already exists, returning to Homepage")
                        self.editor_page()
                        return
                elif Id.lower() == 'u':
                    Num = input("Select a movie pair #: ")

                    # Checks whether the input is 
                    if (not Num.isnumeric() or (Num.isnumeric() and int(Num) >= len(Results))):
                        print("Invalid input, returning to homepage")
                        self.editor_page()
                        return
                    Num = int(Num)

                    Score = 0
                    # Checks whether the score is a float
                    try:
                        Score = float(input("Input a score: "))
                    except:
                        print("Numeric score expected, returning to homepage")
                        self.editor_page()
                        return
                    # Exists in the recommendations list, updating
                    if Results[int(Num)][3] == "Yes":
                        # Updates the score
                        self.cursor.execute('''UPDATE recommendations
                            SET score = :score
                            WHERE (watched = :m1 AND recommended = :m2) OR (watched = :m2 AND recommended = :m1);''',{"score":Score,"m1":Results[int(Num)][0],"m2":Results[int(Num)][1]})
                        self.connection.commit()
                        self.editor_page()
                        return
                    else:
                        print("Invalid ID, returning to Homepage")
                        self.editor_page()
                        return
                else:
                    print("Invalid option")
                    self.editor_page()
                    return
            else:
                print('No pairs found')
                self.editor_page()
                return
        else:
            print('invalid timeframe')
            self.editor_page()
            return
                    
    def add_movie(self):
        print("Enter the movie info")

        # promt user for movie id, title, year, and runtime
        Id = input("Movie ID: ")
        Title = input("Movie Title: ")
        Year = input("Movie Year: ")
        Runtime = input("Movie Runtime: ")
        if Runtime.isnumeric() and Year.isnumeric() and Id.isnumeric():
            # search the table to check if the id exists
            self.cursor.execute('''
                SELECT m.mid
                FROM movies m
                WHERE m.mid=?;
                ''',(Id,))
            Result = self.cursor.fetchone()
            if Result:
                # if it exists
                print("ID already exists")
                self.add_movie()
                return
            else:
                # add the values into the movies table
                self.cursor.execute('''INSERT INTO movies VALUES(?,?,?,?);''',(Id,Title,Year,Runtime))
                # promt user to add a case 
                self.connection.commit()
                self.add_cast(Id)
        else:
            print("Numeric input expected, try again!")
            self.add_movie()
            return

    def add_cast(self,movie_id):
        Id = input("Add or find a cast member by id, or 'E' to cancel: ").lower()
        if Id.lower() == 'e':
            self.editor_page()
            return

        else:
            # check if the cast member already exists
            self.cursor.execute('''
            SELECT name, birthYear
            FROM moviePeople
            WHERE pid=?;
            ''',(Id,))
            Result = self.cursor.fetchone()
            if Result:
                # if cast member exist, print the relevant information
                print("Found User")
                print("Name: " + str(Result[0]))
                print("Birth Year: " + str(Result[1]))
            else:
                # if the cast member doesn't exist prompt the user to enter the missing fields to add to the database
                print("No User Found, Input Fields to Add")
                Name = input("Name: ")
                Year = input("Year: ")

                if (not Year.isnumeric()):
                    print("Integer input expected, returning to homepage")
                    self.editor_page()
                    return
                Year = int(Year)

                # insert new cast member into moviePeople
                self.cursor.execute('''INSERT INTO moviePeople VALUES(?,?,?);''',(Id,Name,Year))
                self.connection.commit()
            # promt user for the cast member's role in the movie add it to casts
            Role = input("Enter the cast member's role: ")
            self.cursor.execute('''INSERT INTO casts VALUES(?,?,?);''',(movie_id,Id,Role))
            self.connection.commit()
            # promt user to check if they want to add multiple cast members
            self.add_cast(movie_id)
        
        
            
    def login(self):
        # get username and password from user input
        print("Enter your credentials to login\n")
        Id = input("User ID:")
        Password = getpass.getpass("Password: ")
        # check if the user is a customer and change to customer page
        self.cursor.execute('''
            SELECT cid, name
            FROM customers c
            WHERE c.pwd = :Password AND c.cid = :Id;
            ''',{"Password":Password,"Id":Id})
        result = self.cursor.fetchone()
        if result:
            # Customer
            self.Cid = result[0]
            self.Name = result[1]
            self.customer_page()
            return
        # check if user is a editor and change to editor page
        else:
            self.cursor.execute('''
            SELECT eid
            FROM editors e
            WHERE e.pwd = :Password AND e.eid = :Id;
            ''',{"Password":Password,"Id":Id})
            result = self.cursor.fetchone()
            if result:
                # Editor
                self.editor_page()
            # password not in the database
            else:
                print("Incorrect password inputted, please try again")
                self.login()
                return

    def start(self):
        #  ask user for input and call corrsponding function
        Choice = input("Do you wish to login (L), sign up (S), or exit(E)? ")
        if Choice.lower() == "l":
            self.login()
            return
        elif Choice.lower() == "s":
            self.signup()
            return
        elif Choice.lower() == "e":
            exit()
        else:
            print("Invalid Choice")
            self.start()

    def signup(self):
        # ask user for id and password
        new_cid = input("Enter a unique CID: ").lower()
        new_password = getpass.getpass("Enter a password: ")
        new_name = input("Enter your name: ")
        # check if the id already exists
        self.cursor.execute('''
            SELECT cid
            FROM customers
            WHERE cid = :Id;
            ''',{"Id":new_cid})
        result = self.cursor.fetchone()
        if result:
            # if it exists get user to enter different credentials
            print("ID already exists")
            self.signup()
            return
        else:
            # if it doesn't exist, add usuer to the customer table
            self.cursor.execute('''INSERT INTO customers VALUES(?,?,?);''',(new_cid,new_name,new_password))
            self.connection.commit()
            self.start()
            return

def main():
    # get database input path
    if len(sys.argv) == 2:
        path = sys.argv[1]
        # intializing the app
        New_App = App()
        New_App.connect(path)
        New_App.start()

        New_App.connection.commit()
        New_App.connection.close()
        return
    else:
        print("Invalid quantity of command line arguments")


if __name__ == "__main__":
    main()
