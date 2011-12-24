
function showData (title, x){
    //http://www.quirksmode.org/js/popup.html
    ugly_but_reportedly_necessary_global = window.open('', 'budget_window',
						       'height=400, width=600');
    var d = ugly_but_reportedly_necessary_global.document;

    var mk = function (p, n) {
	var e = d.createElement(n);
	p.appendChild(e);
	return e;
    }

    mk(d.body, 'h1').textContent = title;
    mk(d.body, 'pre').textContent = JSON.stringify(x);
}

function iwmdb(id) {
    var tl_elt = document.getElementById(id);
    var btn = document.createElement('button');
    btn.textContent='IWMDB @@';
    tl_elt.parentNode.appendChild(btn);
    btn.addEventListener("click", function(event) {
	var tl = new $MW.TxnList("transaction-list",{prefix:"transaction-"});
	$MC.useJson(C.JSON_TRANSACTIONS,
		    function (trxs){
			alert('# trxs: ' + trxs.length);
			showData('Transaction Data', trxs);
			ap.setItemsData(trxs);
		    });
    });
}

iwmdb("transaction-list");
