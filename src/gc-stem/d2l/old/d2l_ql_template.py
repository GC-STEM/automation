# -*- coding: 'utf_8' -*-

from pathlib import Path  # Object-oriented filesystem paths
import csv                # CSV file reading and writing
import os                 # Miscellaneous operating system dependent interfaces

# Set current working directory.
# os.chdir('C:\\tst1')
os.chdir("C:\\Users\\username\\OneDrive - University of Arizona\\Documents\\_Programming\\Python\\Scripts\\mad_quiz")
print("Setting current working directory to:\n", Path.cwd(),"\n")

# Open outputFile and create csv.writer object
outputFile = open('template_ql.csv', 'w', newline='')
outputWriter = csv.writer(outputFile)

# MITRE course goals (cg) and lesson learning objectives (lo)
crs0 = 'MITRE ATT&CK® Defender (MAD) ATT&CK® Fundamentals (MADF)'

cg01  = 'Understand the structure and philosophy that continually shapes ATT&CK®'
cg02  = 'Identify the available ATT&CK® resources and operational use cases'
cg03  = 'Recognize how ATT&CK® empowers defenders through understanding threats'


mod01  = 'Module 1 | Understanding ATT&CK®'

les011 = 'Lesson 1.1 | Introduction to ATT&CK®'
lo0111 = 'LO 1.1.1 | Understand the background and motivation for ATT&CK®'
lo0112 = 'LO 1.1.2 | Identify what information is captured in ATT&CK®'
lo0113 = 'LO 1.1.3 | Recognize the structure of ATT&CK®'

les012 = 'Lesson 1.2 | Matrices/Platforms'
lo0121 = 'LO 1.2.1 | Appreciate how matrices are used in ATT&CK®Appreciate how matrices are used in ATT&CK®'
lo0122 = 'LO 1.2.2 | Understand the difference between ATT&CK® platforms'
lo0123 = 'LO 1.2.3 | Identify the relationship between different ATT&CK® platforms'

les013 = 'Lesson 1.3 | Tactics'
lo0131 = 'LO 1.3.1 | Understand what an ATT&CK® Tactic is'
lo0132 = 'LO 1.3.2 | Appreciate how tactics fit into the ATT&CK® TTP model'

les014 = 'Lesson 1.4 | Techniques & Sub-Techniques'
lo0141 = 'LO 1.4.1 | Understand what an ATT&CK® Technique is'
lo0142 = 'LO 1.4.2 | Recognize the differences in techniques and sub-techniques'
lo0143 = 'LO 1.4.3 | Appreciate how techniques and sub-techniques fit into the ATT&CK® TTP model'

les015 = 'Lesson 1.5 | Mitigations'
lo0151 = 'LO 1.5.1 | Understand what an ATT&CK® Mitigation is'
lo0152 = 'LO 1.5.2 | Identify were to find mitigations'
lo0153 = 'LO 1.5.3 | Appreciate how mitigations fit into the ATT&CK® model'

les016 = 'Lesson 1.6 | Data Sources & Detections'
lo0161 = 'LO 1.6.1 | Understand what ATT&CK® data sources and detections are'
lo0162 = 'LO 1.6.2 | Appreciate the relationship between data sources and detections'
lo0163 = 'LO 1.6.3 | Identify how data sources and detections apply to techniques'

les017 = 'Lesson 1.7 | Groups & Software'
lo0171 = 'LO 1.7.1 | Understand what ATT&CK® Group and Software are'
lo0172 = 'LO 1.7.2 | Identify information provided by ATT&CK® about groups and software'
lo0173 = 'LO 1.7.3 | Appreciate how groups and software fit into the ATT&CK® model'

les018 = 'Lesson 1.8 | How ATT&CK® Grows & Evolves'
lo0181 = 'LO 1.8.1 | Understand how and why ATT&CK® changes over time'
lo0182 = 'LO 1.8.2 | Recognize how to track and monitor changes to ATT&CK®'
lo0183 = 'LO 1.8.3 | Identify how to access previous versions of ATT&CK®'

mod02  = 'Module 2 | Benefits of Using ATT&CK®'

les021 = 'Lesson 2.1 | Community Perspective'
lo0211 = 'LO 2.1.1 | Understand the sources of information that build ATT&CK®'
lo0212 = 'LO 2.1.2 | Appreciate the resulting diversity of ATT&CK® knowledge and perspectives'

les022 = 'Lesson 2.2 | Common Language'
lo0221 = 'LO 2.2.1 | Appreciate the common language created by ATT&CK®'
lo0222 = 'LO 2.2.2 | Recognize how this common language can help operations teams communicate and collaborate'

les023 = 'Lesson 2.3 | Quantitative Scorecard'
lo0231 = 'LO 2.3.1 | Understand how ATT&CK® can help us identify and track cybersecurity metrics'
lo0232 = 'LO 2.3.2 | Appreciate the types of questions ATT&CK® can help us address'

les024 = 'Lesson 2.4 | ATT&CK® Navigator'
lo0241 = 'LO 2.4.1 | Understand the structure and purpose of the ATT&CK® Navigator to create visualizations'
lo0242 = 'LO 2.4.2 | Appreciate how to use the ATT&CK® Navigator to create visualizations'

mod03 = 'Module 3 | Operationalizing ATT&CK®'

les031 = 'Lesson 3.1 | Cyber Threat Intelligence'
lo0311 = 'LO 3.1.1 | Understand the importance of cyber threat intelligence in security operations'
lo0312 = 'LO 3.1.2 | Appreciate how ATT&CK® can provide a starting point and structure for tracking intelligence'

les032 = 'Lesson 3.2 | Detection & Analytics'
lo0321 = 'LO 3.2.1 | Identify how ATT&CK® and CTI can help us prioritize and build better detection analytics'

les033 = 'Lesson 3.3 | Threat Emulation'
lo0331 = 'LO 3.3.1 | Understand what threat (or adversary) emulation is'
lo0332 = 'LO 3.3.2 | Appreciate how threat emulation can use behaviors, such as those documented in ATT&CK®, to assess defenses'

les034 = 'Lesson 3.4 | Assessment & Engineering'
lo0341 = 'LO 3.4.1 | Understand how we can capture the results of threat emulation and other outputs to identify gaps in our defenses'
lo0342 = 'LO 3.4.2 | Appreciate how measuring our defenses leads to making informed improvements'

les035 = 'Lesson 3.5 | Putting It All Together into Threat-Informed Defense'
lo0351 = 'LO 3.5.1 | Appreciate how ATT&CK® helps us make better cybersecurity decisions'


crs1 = 'MITRE ATT&CK® Defender (MAD) ATT&CK® for Cyber Threat Intelligence (CTI) (MADC)'



crs2 = 'MITRE ATT&CK® Defender (MAD) ATT&CK® for Security Operations Center (SOC) Assessments (MADS)'



crs3 = 'MITRE ATT&CK® Defender (MAD) ATT&CK® for Adversary Emumlation Methodology (MADE)'



crs4 = 'MITRE ATT&CK® Defender (MAD) ATT&CK® for Threat Hunting Detection Engineering (MADT)'





# Write worksheet header rows to CSV file
outputWriter.writerow([crs,]) # D2L QL Section Level 1
outputWriter.writerow([mod,]) # D2L QL Section Level 2
outputWriter.writerow([les,]) # D2L QL Section Level 3
outputWriter.writerow([lo,])  # D2L QL Section Level 4
outputWriter.writerow([bq,])  # D2L QL Section Level 5
outputWriter.writerow(['',])  # Blank row
outputWriter.writerow(['',])  # Blank row


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
outputWriter.writerow(['//Mandatory', 'TRUE/FALSE'])
outputWriter.writerow(['//Enumeration', 'TRUE/FALSE'])
outputWriter.writerow(['//Random', 'TRUE/FALSE'])
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
outputWriter.writerow(['//Mandatory', 'TRUE/FALSE'])
outputWriter.writerow(['//Enumeration', 'TRUE/FALSE'])
outputWriter.writerow(['//Random', 'TRUE/FALSE'])
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
