<?xml version="1.0" encoding="utf-8"?><!--*- nxml -*-->
<!DOCTYPE html>

<?python from trxtsv import isoDate, numField ?>

<html xmlns="http://www.w3.org/1999/xhtml"
      xmlns:py="http://purl.org/kid/ns#"
      >
  <head profile="http://www.w3.org/2003/g/data-view
		 http://purl.org/NET/erdf/profile">
    <title>${title}</title>
  <link rel="transformation"
	href="http://www.w3.org/2002/12/cal/glean-hcal.xsl"/>
  <style type="text/css">
table.mittravel tbody tr td { border: 2px solid }
table.mittravel tbody tr th { text-align: left }

tbody.vevent tr.trx td { border-top: 1px solid }
tbody.vevent td { padding: 3px; margin: 0}
.amt { text-align: right }
.even { background: grey }
</style>

  </head>
<body>

<table class="mittravel">
<tbody id='${trip["id"]}' class="vevent">
<tr>
  <th>NAME of traveller</th>
  <!-- factor out organizer/vcard handling -->
  <?python who = trip["organizer"] ?>
  <td class="organizer vcard"><u class='fn'>${who["fn"]}</u></td>
</tr>
<tr>
  <th>DESTINATION(S)</th>
  <!-- factor out location/vcard handling -->
  <?python where = trip["location"] ?>
  <td class="location vcard" id="${where['id']}">
    <u class="locality">${where['locality']}</u
    >, <u class="region">${where['region']}</u
    >, <u class="country-name">${where['country-name']}</u>
  </td>
</tr>
<tr>
  <th>START—Date</th>
  <td><abbr class="dtstart" title="${trip['dtstart']}">trip['dtstart']}</abbr></td>
  <td><abbr class="dtend" title="${trip['dtend']}">trip['dtend']}-1@@</abbr></td>
</tr>
<tr>
  <th>PURPOSE of trip</th>
  <td class="note">${trip["note"]}</td>
</tr>

</tbody>

<tbody class="vevent">

<!-- TODO: multiple legs -->
<!-- TODO: derive this from travel itinerary -->
<tr>
  <th>TICKETS $$Amount</th><td>${air["amt"]}</td><td>${air["note"]}</td>
</tr>
<tr>
  <th>TRANSPORTATION—Date/From/To/Mode</th>
  <td>${air["depart"]}</td>
  <td>${air["origin"]}</td>
  <td>${air["destination"]}</td>
  <td>air</td>
</tr>
<tr>
  <th>&#160;</th>
  <td>${air["return"]}</td>
  <td>${air["origin"]}</td>
  <td>${air["destination"]}</td>
  <td>air</td>
</tr>
</tbody>

<?python transactions=list(transactions) ?>
<?python hotels = list(hotel_stays(transactions)) ?>

<tbody>
<tr>
 <th>HOTEL— # of nights?</th>
 <td>${sum([e["duration"] for e in hotels])}</td>
 <th>total $$Amt?</th>
 <td>${sum([e["amt"] for e in hotels])}</td>
</tr>
</tbody>
<tbody class="vevent" py:for="e in hotels">
<tr>
  <th>HOTEL Name</th>
  <td colspan="2" class="location">${e["location"]}</td>
  <td class="note">${e["amt"]}</td>
</tr>
</tbody>

</table>
<table>
<!-- @@TODO: split table every 100 transactions? -->

<!-- transactions -->
<tbody py:for="t in []" class='vevent'>
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
