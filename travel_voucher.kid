<?xml version="1.0" encoding="utf-8"?><!--*- nxml -*-->
<!DOCTYPE html>

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

th.startblock { margin-top: 1em }
tbody.vevent tr.trx td { border-top: 1px solid }
tbody.vevent td { padding: 3px; margin: 0}
.amt { text-align: right }
.even { background: grey }
</style>

  </head>
<body>

<table class="mittravel">
<tbody id='${trip.id}' class="vevent">
<tr>
  <th class="startblock">NAME of traveller</th>
  <!-- factor out organizer/vcard handling -->
  <?python who = trip["organizer"] ?>
  <td class="organizer vcard" colspan="2"><u class='fn'>${who.fn}</u></td>
</tr>
<tr>
  <th>DESTINATION(S)</th>
  <!-- factor out location/vcard handling -->
  <?python where = trip.location ?>
  <td class="location vcard" id="${where.id}" colspan="4">
    <u class="locality">${where.locality}</u
    >, <u class="region">${where.region}</u
    >, <u class="country-name">${where['country-name']}</u>
  </td>
</tr>
<tr>
  <th>START—Date</th>
  <td><abbr class="dtstart" title="${trip['dtstart']}">${trip['dtstart']}</abbr></td>
  <td><abbr class="dtend" title="${trip['dtend']}">${trip['dtend']}-1@@</abbr></td>
</tr>
<tr>
  <th class="startblock">PURPOSE of trip</th>
  <td class="note" colspan="4">${trip["note"]}</td>
</tr>

</tbody>

<?python
tot_adv = 0
tot_trip = 0
?>

<tbody class="vevent">

<!-- TODO: multiple legs -->
<!-- TODO: derive this from travel itinerary -->
<tr>
  <th class="startblock">TICKETS $$Amount</th>
  <?python a = air["amt"]; tot_adv += a; tot_trip += a ?>
  <td class="amt">$a</td>
  <td>${air["note"]}</td>
</tr>

<!-- assume MIT buys tickets -->

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
  <td>${air["destination"]}</td>
  <td>${air["origin"]}</td>
  <td>air</td>
</tr>
</tbody>

<?python transactions=list(transactions) ?>
<?python hotels = list(find_hotels(transactions)) ?>

<tbody>
<tr>
 <th>HOTEL— # of nights?</th>
 <td>${sum([e["duration"] for e in hotels])}</td>
 <th>total $$Amt?</th>

 <!-- TODO: account for direct-billed hotels -->
 <?python a = sum([e["amt"] for e in hotels]); tot_trip += a ?>
 <td class="amt">$a</td>
</tr>
</tbody>
<tbody class="vevent" py:for="e in hotels">
<tr>
  <th>HOTEL Name</th>
  <td class="dtstart">${e["dtstart"]}</td>
  <td class="summary location" colspan="2">${e["location"]}</td>
  <td class="note amt">${e["amt"]}</td>
</tr>
</tbody>

<?python meals = list(find_meals(transactions)) ?>
<tbody>
<tr>
 <th>MEALS—# of meals?</th>
 <td>${len(meals)}</td>
 <th>total $$Amt?</th>
 <?python a = sum([e["amt"] for e in meals]); tot_trip += a ?>
 <td class="amt">$a</td>
</tr>
</tbody>

<?python Heading="MEALS DETAIL" ?>
<tbody class="vevent" py:for="e in meals">
<tr>
  <th>$Heading</th>
  <td class="dtstart">${e["dtstart"]}</td>
  <td class="summary location" colspan="2">${e["location"]}</td>
  <td class="note amt">${e["amt"]}</td>
</tr>
<?python Heading="" ?>
</tbody>

<?python taxis = list(find_taxis(transactions)) ?>
<?python Heading="TAXI, BUS, ETC." ?>
<tbody class="vevent" py:for="e in taxis">
<tr>
  <th>$Heading</th>
  <td class="dtstart">${e["dtstart"]}</td>
  <td class="summary location">${e["location"]}</td>
  <td class="category">${e["category"]}</td>

  <?python a = e["amt"]; tot_trip += a ?>

  <td class="note amt">$a</td>
</tr>
<?python Heading="" ?>
</tbody>

<?python others = list(find_others(transactions)) ?>
<?python Heading="OTHER EXPENSES (itemize)" ?>
<tbody class="vevent" py:for="e in others">
<tr>
  <th>$Heading</th>
  <td class="dtstart">${e["dtstart"]}</td>
  <td class="summary" colspan="2">${e["summary"]}</td>

  <?python a = e["amt"]; tot_trip += a ?>
  <td class="note amt">$a</td>
</tr>
<?python Heading="" ?>
</tbody>

<tbody>
<?python tot_adv += find_advance_amount(transactions) ?>
<tr><th>TRAVEL ADVANCE $$AMT</th><td class="amt">${tot_adv}</td></tr>
<tr><th>TOTAL TRIP AMOUNT</th><td class="amt">${tot_trip}</td></tr>
<tr><th>TOTAL DUE TO TRAVELER</th>
    <td class="amt">${tot_trip - tot_adv}</td></tr>
</tbody>
</table>

</body>
</html>
