
function iwmdb(id) {
    alert(location.href);
    var tl_elt = document.getElementById(id);
    var btn = document.createElement('button');
    btn.textContent='IWMDB @@';
    tl_elt.parentNode.appendChild(btn);
    btn.addEventListener("click", function(event) {
        alert('IWMDB!');
        alert('$MW: ' + $MW);

	var tl = new $MW.TxnList("transaction-list",{prefix:"transaction-"});
	$MC.useJson(C.JSON_TRANSACTIONS,
		    function (trxs){
			alert('# trxs: ' + trxs.length);
			ap.setItemsData(trxs);
		    });
    });
}

iwmdb("transaction-list");
