Accessing Google Spreadsheets from Node.js
Posted at March 4, 2014 07:00 am by Nicholas C. Zakas
ack: http://www.nczonline.net/blog/2014/03/04/accessing-google-spreadsheets-from-node-js/


`SPREADSHEET_ID` - from ?key=... part of spreadsheet URL in google sheets
`WORKSHEET_NAME` - from the tabs at the bottom of the spreadsheet

`OAUTH_EMAIL` - from google developer console, as in article above[1]
`PEM_KEY` - path to key from google developer console, converted to PEM format as in [1]

$ openssl pkcs12 -in fin-sync-ETC.p12 -out fin-sync-ETC.pem -nodes

then run:

fin-sync$ nodejs sync1.js
