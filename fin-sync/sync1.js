var Spreadsheet = require('edit-google-spreadsheet');

Spreadsheet.load({
    debug: true,
    spreadsheetId: process.env.SPREADSHEET_ID,
    worksheetName: process.env.WORKSHEET_NAME,

    oauth : {
        email: process.env.OAUTH_EMAIL,
        keyFile: process.env.PEM_KEY
    }

}, function sheetReady(err, spreadsheet) {

    if (err) {
        throw err;
    }

    spreadsheet.receive(function(err, rows, info) {
        if (err) {
            throw err;
        }

        console.dir(rows);
        console.dir(info);
    });

});
