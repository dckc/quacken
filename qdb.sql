CREATE TABLE Accounts (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 ,   parent INTEGER 
 );
CREATE TABLE Transactions (
  id INTEGER PRIMARY KEY 
 ,   acct INTEGER 
 ,   date DATE 
 ,   payee TEXT 
 ,   num TEXT 
 ,   ty TEXT 
 ,   memo TEXT 
 );
CREATE TABLE Splits (
  id INTEGER PRIMARY KEY 
 ,   trx INTEGER 
 ,   acct INTEGER 
 ,   cat INTEGER 
 ,   clr TEXT 
 ,   memo TEXT 
 ,   subtot FLOAT 
 );
CREATE TABLE Payees (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 );
CREATE TABLE Classes (
  id INTEGER PRIMARY KEY 
 ,   name TEXT 
 );
