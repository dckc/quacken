<?xml version="1.0" encoding="utf-8"?><!--*- nxml -*-->
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:py="http://purl.org/kid/ns#"
      >
  <head profile="http://www.w3.org/2003/g/data-view
		 http://purl.org/NET/erdf/profile">
    <title>SxSWi Travel Expense Voucher</title>
    <!-- @@TODO: refactor as extension of MIT expense voucher template -->
  <link rel="transformation"
	href="http://www.w3.org/2002/12/cal/glean-hcal.xsl"/>
  <style type="text/css">
tbody.vevent tr.trx td { border-top: 1px solid }
tbody.vevent td { padding: 3px; margin: 0}
.amt { text-align: right }
.even { background: grey }
</style>

<?python from trxtsv import isoDate, numField ?>

  </head>
<body>

<h1>Transactions</h1>
<div>Filter info: ${`criteria`}</div>

<table>
<!-- @@TODO: split table every 100 transactions? -->

<tbody py:for="t in transactions" class='vevent'>
 <?python date = t["trx"]["date"] ?>
 <!-- todo grey/parity -->
 <tr class='trx'>
  <td><abbr class='dtstart' title='${isoDate(date)}'>${date}</abbr></td>
  <td>${t["trx"].get("payee",'')}</td> <!-- descElt hcard stuff@@ -->

  <?python num, splitflag, trxty = numField(t["trx"].get('num', '')) ?>

  <td>${num or trxty or ''}</td>
  <td>${t["trx"]['acct']}</td>
 </tr>
 <tr py:for="split in t['splits']" class='split description'>
   <td></td>
   <td>${split.get('memo', '')}</td>
   <td>${split.get('clr', '')}</td>
   <td>${split.get('L', '')}</td>
   <td class='amt'>${split.get('subtot', '')}</td>
</tr>

</tbody>

</table>

</body>
</html>
