
function make_budget_window(){
    var categories = Mint.CategorySearch.getJson();
    var current_income = Mint.PlanningData.getJson(true, new Date());
    var current_spending = Mint.PlanningData.getJson(false, new Date());

    var budget = function(id) {
	for (i=0; i<current_income.bu.length; i++) {
	    var b = current_income.bu[i];
	    if (b.cat == id) {
		return b;
	    }
	}
	for (i=0; i<current_spending.bu.length; i++) {
	    var b = current_spending.bu[i];
	    if (b.cat == id) {
		return b;
	    }
	}
    }
    //http://www.quirksmode.org/js/popup.html
    ugly_but_reportedly_necessary_global = window.open('', 'budget_window',
						       'height=400, width=600');
    var d = ugly_but_reportedly_necessary_global.document;
    var b = d.body;

    var mk = function (p, n) {
	var e = d.createElement(n);
	p.appendChild(e);
	return e;
    }

    mk(b, 'h1').textContent = 'Budget';
    var t = mk(b, 'table');
    var thead = mk(t, 'tr')
    mk(thead, 'th').textContent = 'id';
    mk(thead, 'th').textContent = 'Category';
    mk(thead, 'th').textContent = 'Subcategory';
    mk(thead, 'th').textContent = 'Amount';
    mk(thead, 'th').textContent = 'Budget';

    var docat = function(cat, subcat) {
	var b, row = mk(t, 'tr');
	mk(row, 'td').textContent = subcat ? subcat.id : cat.id;
	mk(row, 'td').textContent = cat.value;
	if (subcat) {
	    mk(row, 'td').textContent = subcat.value;
	    b = budget(subcat.id);
	    if (!b) {
		YAHOO.log('no budget for subcat: ' + subcat.value);
	    }
	} else {
	    mk(row, 'td');
	    b = budget(cat.id);
	    if (!b) {
		YAHOO.log('no budget for: ' + cat.value);
	    }
	}

	if (b) {
	    mk(row, 'td').textContent = b.amt;
	    mk(row, 'td').textContent = b.bgt;
	}
    }

    categories.forEach(function(cat) {
	docat(cat);
	var row = mk(t, 'tr')
	cat.children.forEach(function(subcat) {
	    docat(cat, subcat);
	});
    });
}

make_budget_window();

/*
Mint.PlanningData.getJson(true, apr);
Mint.CategorySearch.getJson();

apr = new Date(2011, 03, 01);
// Fri Apr 01 2011 00:00:00 GMT-0500 (CDT)
Object
{
bu: Array[6]
0: Object
amt: 1522.5
bgt: 1250
cat: 1050996
ex: false
id: 25616372
pid: 30
st: 1
type: 0
}

*/
