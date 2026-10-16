# -*- coding: 'utf_8' -*-

from pathlib import Path  # Object-oriented filesystem paths
import csv                # CSV file reading and writing
import os                 # Miscellaneous operating system dependent interfaces

# Set current working directory.
# os.chdir('C:\\tst1')
os.chdir("C:\\Users\\username\\OneDrive - University of Arizona\\Documents\\_Programming\\Python\\Scripts\\mad_quiz")
print("Setting current working directory to:\n", Path.cwd(),"\n")

# Open outputFile and create csv.writer object
outputFile = open('test_ql.csv', 'w', newline='')
outputWriter = csv.writer(outputFile)

# D2L Sample Question Import Text
outputWriter.writerow(['//(Note: The \'images\' folder is assumed to be in the "/content/<course path>/" directory)',])
outputWriter.writerow(['//Question Text is always a required field',])
outputWriter.writerow(['// An ID will be generated using the (Course code)-(Question number) if an ID is not specified for a question',])
outputWriter.writerow(['',])  # Blank row between questions.
outputWriter.writerow(['// Please ensure that the CSV file is saved as "CSV UTF-8" encoded to ensure that non-ASCII characters like Ã , Ã¸, Ã© and other are able to be correctly imported',])  # Blank row between questions.
outputWriter.writerow(['',])  # Blank row between questions.

# Written Response / Long Answer Question
outputWriter.writerow(['//WRITTEN RESPONSE QUESTION TYPE',])
outputWriter.writerow(['///This sample question also shows how you can set a question caID for the question of format {Course Code}-{Question Number}',])
outputWriter.writerow(['NewQuestion', 'WR'])
outputWriter.writerow(['ID', 'CHEM110-234'])
outputWriter.writerow(['Title', 'This is a written response question'])
outputWriter.writerow(['QuestionText', 'This is the question text for WR1'])
outputWriter.writerow(['Points', '1'])
outputWriter.writerow(['Difficulty', '7'])
outputWriter.writerow(['Image', 'images/LA1.jpg'])
outputWriter.writerow(['InitialText', 'This is the initial text'])
outputWriter.writerow(['AnswerKey', 'This is the answer key text'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
outputWriter.writerow(['',])  # Blank row between questions.
outputWriter.writerow(['',])  # Blank row between questions.

# Short Answer Question
outputWriter.writerow(['//SHORT ANSWER QUESTION TYPE',])
outputWriter.writerow(['//Answers must include text in column3',])
outputWriter.writerow(['NewQuestion', 'SA'])
outputWriter.writerow(['ID', 'CHEM110-235'])
outputWriter.writerow(['Title', 'This is a short answer question'])
outputWriter.writerow(['QuestionText', 'This is the question text for SA1'])
outputWriter.writerow(['Points', '5'])
outputWriter.writerow(['Difficulty', '2'])
outputWriter.writerow(['Image', 'images/SA1.jpg'])
outputWriter.writerow(['InputBox', '3', '40'])
outputWriter.writerow(['Answer', '100', 'This is text for answer 1', 'regexp'])
outputWriter.writerow(['Answer', '50', 'This is text for answer 2'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
outputWriter.writerow(['',])  # Blank row between questions.

# Matching Question
outputWriter.writerow(['//MATCHING QUESTION TYPE',])
outputWriter.writerow(['//Choices and Matches must include text in column3',])
outputWriter.writerow(['NewQuestion', 'M'])
outputWriter.writerow(['ID', 'CHEM110-236'])
outputWriter.writerow(['Title', 'This is a matching question'])
outputWriter.writerow(['QuestionText', 'This is the question text for M1'])
outputWriter.writerow(['Points', '2'])
outputWriter.writerow(['Difficulty', '2'])
outputWriter.writerow(['Image', 'images/M1.jpg'])
outputWriter.writerow(['Scoring', 'EquallyWeighted']) # List scoring options here.
outputWriter.writerow(['Choice', '1', 'Choice 1'])
outputWriter.writerow(['Match', '1', 'Match 1'])
outputWriter.writerow(['Choice', '2', 'Choice 2'])
outputWriter.writerow(['Match', '2', 'Match 2'])
outputWriter.writerow(['Choice', '3', 'Choice 3'])
outputWriter.writerow(['Match', '3', 'Match 3'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
#outputWriter.writerow(['//Random', 'On'])
outputWriter.writerow(['',])  # Blank row between questions.

# Multiple Choice Question
outputWriter.writerow(['//MULTIPLE CHOICE QUESTION TYPE',])
outputWriter.writerow(['//Options must include text in column3',])
outputWriter.writerow(['NewQuestion', 'MC'])
outputWriter.writerow(['ID', 'CHEM110-237'])
outputWriter.writerow(['Title', 'This is a multiple choice question'])
outputWriter.writerow(['QuestionText', 'This is the question text for MC1'])
outputWriter.writerow(['Points', '1'])
outputWriter.writerow(['Difficulty', '1'])
outputWriter.writerow(['Image', 'images/MC1.jpg'])
outputWriter.writerow(['Option', '100', 'This is the correct answer', '', 'This is feedback for option 1'])
outputWriter.writerow(['Option', '0', 'This is incorrect answer 1', '', 'This is feedback for option 2'])
outputWriter.writerow(['Option', '0', 'This is incorrect answer 2', '', 'This is feedback for 0ption 3'])
outputWriter.writerow(['Option', '25', 'This is partially correct', '', 'This is feedback for 0ption 4'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
#outputWriter.writerow(['//Random', 'On'])
outputWriter.writerow(['',])  # Blank row between questions.
outputWriter.writerow(['',])  # Blank row between questions.

# True/False Question
outputWriter.writerow(['//TRUE / FALSE QUESTION TYPE',])
#outputWriter.writerow(['//MLO','0.0.0'])
outputWriter.writerow(['NewQuestion', 'TF'])
outputWriter.writerow(['ID', 'CHEM110-238'])
outputWriter.writerow(['Title', 'This is a True/False question'])
outputWriter.writerow(['QuestionText', 'This is the question text for TF1'])
outputWriter.writerow(['Points', '1'])
outputWriter.writerow(['Difficulty', '1'])
outputWriter.writerow(['Image', 'images/TF1.jpg'])
outputWriter.writerow(['TRUE', '100', 'Correct. This is feeback for TRUE.'])
outputWriter.writerow(['FALSE', '0', 'Incorrect. This is feedback for FALSE.'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
outputWriter.writerow(['',])  # Blank row between questions.
outputWriter.writerow(['',])  # Blank row between questions.

# Multiple Select Question
outputWriter.writerow(['//MULTISELECT QUESTION TYPE',])
outputWriter.writerow(['//Options must include text in column3',])
outputWriter.writerow(['NewQuestion', 'MS'])
outputWriter.writerow(['ID', 'CHEM110-239'])
outputWriter.writerow(['Title', 'This is a Multi-Select question'])
outputWriter.writerow(['QuestionText', 'This is the question text for MS1'])
outputWriter.writerow(['Points', '10'])
outputWriter.writerow(['Difficulty', '5'])
outputWriter.writerow(['Image', 'images/MS1.jpg'])
outputWriter.writerow(['Scoring', 'RightAnswers']) # List scoring options here.
outputWriter.writerow(['Option', '1', 'This is option 1 text', '', 'This is feedback for option 1'])
outputWriter.writerow(['Option', '0', 'This is option 2 text', '', 'This is feedback for option 2'])
outputWriter.writerow(['Option', '1', 'This is option 3 text', '', 'This is feedback for option 3'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
#outputWriter.writerow(['//Random', 'On'])
outputWriter.writerow(['',])  # Blank row between questions.
outputWriter.writerow(['',])  # Blank row between questions.

# Ordering Question
outputWriter.writerow(['//ORDERING QUESTION TYPE',])
outputWriter.writerow(['//Items must include text in column2',])
outputWriter.writerow(['NewQuestion', 'O'])
outputWriter.writerow(['ID', 'CHEM110-240'])
outputWriter.writerow(['Title', 'This is an ordering question'])
outputWriter.writerow(['QuestionText', 'This is the question text for O1'])
outputWriter.writerow(['Points', '2'])
outputWriter.writerow(['Difficulty', '2'])
outputWriter.writerow(['Scoring', 'RightAnswers']) # List scoring options here.
outputWriter.writerow(['Image', 'images/O1.jpg'])
outputWriter.writerow(['Item', 'This is text for item 1', 'NOT HTML','This is feeback for item 1.'])
outputWriter.writerow(['Item', 'This is text for item 2', 'HTML','This is feeback for item 2.'])
outputWriter.writerow(['Hint', 'This is the hint text'])
outputWriter.writerow(['Feedback', 'This is the feedback text'])
outputWriter.writerow(['',])  # Blank row between questions.


# Close outputFile
outputFile.close()
