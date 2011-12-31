use dm93finance;
SET sql_safe_updates=0;

/* We need unique names for accounts for this work. */
create unique index accounts_name on accounts (name(250));

/* We assume any mint transactions whose accounts (e.g. Cash) don't match
 * existing gnucash accounts by name can be ignored. Eyeball them: */
select * from minttrx where account in (

select ma.* from
(select distinct account from minttrx) ma
left join accounts ga on ga.name = ma.account
where ga.name is null

);

-- guid column is only 32 chars long
select length(replace(uuid(), '-', ''));

/* Ensure accounts mentioned in transactions are in gnucash.
 * This design pre-dates the availability of the canonical mint account data,
 * so it's kinda wonky.
 */
insert into accounts
select replace(uuid(), '-', '') as guid
     , mc.category as name
     , mc.account_type
     , usd.guid as commodity_guid
     , usd.fraction as commodity_scu
     , 0 as non_std_scu
     , parent.guid as parent_guid
     , '' as code
     , '' as description
     , 0 as hidden
     , 0 as placeholder
from (select category, case when tot > 0 then 'INCOME' else 'EXPENSE' end as account_type
   from (
     select category
          , sum(amount * case when isDebit = 1 then -1 else 1 end) as tot
     from minttrx
     group by category) x) mc
join commodities usd on usd.mnemonic='USD'
join accounts parent on parent.name=
   case when mc.account_type = 'EXPENSE' then 'Spending' else 'Income' end
order by 3, 2;
-- 124 row(s) affected

/* Now that we have the JSON category data from mint... */
drop table mint_budget_categories;
create table mint_budget_categories (
id	int /* not null auto_increment*/,
category varchar(80),
subcategory varchar(80),
amount decimal(8, 2),
budget decimal(8, 2) /*,
  PRIMARY KEY (id)*/
);

load data infile '/home/connolly/qtrx/dm93finance/budget_mint.csv'
into table mint_budget_categories
fields terminated by ',' optionally enclosed by '"'
ignore 1 lines;

delete from mint_budget_categories where id=0;
alter table mint_budget_categories
add constraint primary key (id);

update mint_budget_categories
set subcategory = null
where subcategory = '';

/* ensure all parent accounts exist*/
insert into accounts
select replace(uuid(), '-', '') as guid
     , mc.category as name
     , 'EXPENSE' account_type
     , usd.guid as commodity_guid
     , usd.fraction as commodity_scu
     , 0 as non_std_scu
     , parent.guid as parent_guid
     , '' as code
     , '' as description
     , 0 as hidden
     , 0 as placeholder
from mint_budget_categories mc
join accounts parent on parent.name = 'Mint Expenses'
join commodities usd on usd.mnemonic = 'USD'
where subcategory is null
and category not in (select name from accounts);

/* Use gnucash account.code to correlate with mint categories. */
update
-- select * from
 accounts a
join (
select id, category
from mint_budget_categories
where subcategory is null
union
select id, subcategory
from mint_budget_categories
where subcategory is not null) mc
on mc.category = a.name
set a.code = mc.id
;


/* organize gnucash accounts according to mint structure */
update
-- select p.name, a.name from
accounts a
join mint_budget_categories mc
  on mc.subcategory = a.name
 and a.account_type in ('INCOME', 'EXPENSE')
join accounts p
  on mc.category = p.name
-- order by p.name, a.name
set a.parent_guid = p.guid
;

/* Aside: Which transactions from mint accounts don't have OFX online_id's?
 * They seem to all be transfers, which I think I messed around with manually. */
select tx.post_date, a.name, s.memo, s.value_num / s.value_denom amount
from transactions tx
join splits s on s.tx_guid = tx.guid
join accounts a on s.account_guid = a.guid
 and a.name in (select distinct account from minttrx)
left join slots on slots.obj_guid = s.guid and slots.name = 'online_id'
where slots.obj_guid is null;

/* Flag parents by counting children. */
update minttrx p set p.children=null;
update minttrx p
join (
  select count(*) qty, parent
  from minttrx
  where parent is not null
  group by parent) ea
on ea.parent = p.id
set p.children = ea.qty;

/* Eyeball parents and children. */
select * from minttrx
where children > 0 or isChild = 1
order by date, (case when isChild=1 then parent else id end);


/* Just a few dups of this sort... */
select count(*), date, account, omerchant, isDebit, amount
from minttrx
group by date, account, omerchant, isDebit, amount
having count(*) > 1
order by date desc;

-- alter table minttrx drop index minttrx_sig;
create index minttrx_sig on minttrx (account, omerchant);

create or replace view tx_desc as
select spa.guid, tx.post_date, a.guid account_guid, a.name account, value_num
     /* My bank repeats the OFX NAME in the MEMO, but Discover doesn't Ugh. */
     , tx.description
     , case when spa.memo > '' then spa.memo else null end memo
     , case when ofxmemo.obj_guid is not null and ofxmemo.string_val like '%Memo:%'
       then substring_index(ofxmemo.string_val, 'Memo:', -1)
       else null
       end ofx_memo
from transactions tx
join splits spa on spa.tx_guid = tx.guid
left join slots ofxmemo on ofxmemo.obj_guid = tx.guid
     and ofxmemo.name = 'notes'
join accounts a on spa.account_guid = a.guid;

-- drop table mint_gc_matches;
create table mint_gc_matches as
select gcand.guid, gcand.post_date, timestampdiff(day, gcand.post_date, mcand.date) ddelta
     , mcand.*, cat.guid cat_guid, account_guid
from (
/* Candidates: id, parts, date, account, omerchant, signed amount
   where amount is the total in the isChild case. */
select mx.id, tots.*, mx.categoryId, mx.category
from minttrx mx
join (
  select count(*) parts, date, account, omerchant description
       , sum(case when isDebit = 1 then -amount else amount end) amount
  from minttrx
  where isChild = 1 and isDuplicate = 0
  group by date, account, omerchant) tots
on mx.date = tots.date
and mx.account = tots.account
and mx.omerchant = tots.description
where mx.isChild = 1
and isDuplicate = 0
and category not in ('Exclude From Mint')

union all

select id, 1 parts, date, account
     /* patch wierd Check #nnnn #nnnn */
     , case when omerchant like 'Check #% #%'
       then substr(omerchant, 1, length('Check #9999'))
       else omerchant end d
     , case when isDebit = 1 then - amount else amount end amount
     , categoryId, category
from minttrx
where isChild != 1
and isDuplicate = 0
and category not in ('Exclude From Mint')
) mcand
join (
 select distinct * from (
  select guid, post_date, account_guid, account, value_num, description from tx_desc
  union all
  select guid, post_date, account_guid, account, value_num, memo description from tx_desc
  where memo is not null
  union all
  select guid, post_date, account_guid, account, value_num, ofx_memo description from tx_desc
  where ofx_memo is not null
 ) gc0 where account in (select distinct account from minttrx)
) gcand
on timestampdiff(day, gcand.post_date, mcand.date) between -12 and 10 -- mcand.date = cast(gcand.post_date as date)
and mcand.account = gcand.account
-- todo: chase down full memos
and substr(mcand.description, 1, 32) = substr(gcand.description, 1, 32)
and mcand.amount * 100 = gcand.value_num
join accounts cat on cat.name = mcand.category;


-- eyeball the results:
-- select * from mint_gc_matches;

/* If a given gnucash split matches mint transactions with different dates,
   delete all but the closest in time. */
delete mm from mint_gc_matches mm
join (
-- select *
select bad.guid, bad.id
from mint_gc_matches bad
join mint_gc_matches mm
  on mm.guid = bad.guid
and abs(mm.ddelta) < abs(bad.ddelta)) bad
where mm.id = bad.id and mm.guid = bad.guid;

/* Of the remaining dups, this shows any ambiguities in the resulting categories.
 * None. Yay. */
select count(*), id from (
  select distinct id, category from (
    -- This subquery lets you eyeball the few remaining dups.
    select qty, mm.id id_check, category cat_check, mm.* from (
      select count(*) qty, id
      from mint_gc_matches
      group by id
      having count(*) > 1
      order by 1 desc) dups
    join mint_gc_matches mm on dups.id = mm.id
    order by mm.id) dups
  ) x
group by id
having count(*) > 1;

-- TODO: fix 'Dave &amp; Buster''s'
-- TODO: update tx.description using full ofx memo

/* just a few mismatches... check dates: */
-- BUG: DAVE & BUSTERS etc.
select mx.*
from minttrx mx
left join mint_gc_matches mm
  on mm.id = mx.id
where mm.id is null
  -- spaces, &
  and mx.id not in ('296017984', '295931876', '298228734', '305034939', '311162603', '384319337', '384319338')
  -- beginning of my epoch
  and mx.date > date '2010-06-30'
  and mx.category not in ('Exclude From Mint')
  -- I have only reconciled one month of discover
  and not (mx.account = 'Discover' and mx.date > date '2010-07-14')
  and not (mx.account = 'PERFORMANCE CHECKING' and mx.date > date '2011-11-16')
  -- haven't done these
  and mx.account not in ('Costco TrueEarnings Card', 'SAVINGS', 'Home Depot CC')
order by mx.date;

/* And now the moment we've all been waiting for...
what are we about to update?

Ugh... I'm missing cat_split_guid */
select cat.name ocat, category, cat_split.value_num / cat_split.value_denom, mm.*
from mint_gc_matches mm
join splits spa on mm.guid = spa.guid
join transactions tx on spa.tx_guid = tx.guid
join splits cat_split on cat_split.tx_guid = tx.guid
 and cat_split.value_num = - spa.value_num
join accounts cat on cat_split.account_guid = cat.guid
where cat.account_type in ('CASH', 'INCOME', 'EXPENSE')
 and cat_split.account_guid != mm.cat_guid
and mm.parts=1
order by mm.post_date, cat_split.guid;


update splits cat_split
join mintmatch mm on mm.cat_split_guid = cat_split.guid
join mintexport mx on mm.mint_id = mx.id
join accounts cat on cat_split.account_guid = cat.guid
set cat_split.account_guid = mm.cat_guid,
cat_split.memo = mx.notes
where cat.account_type in ('CASH', 'INCOME', 'EXPENSE')
-- todo: labels
;

-- TODO: clean up transaction descriptions for 1-N splits
update transactions tx
join mintmatch mm on mm.tx_guid = tx.guid
join mintexport mx on mm.mint_id = mx.id
set tx.description = mx.description
where mm.split_qty = 1;

/* manual clean-up */
select * from mintexport mx
left join mintmatch mm on mm.mint_id = mx.id
where
-- mx.amount = 12.25
mx.original_description like '%CULVER%'
order by date;


/* replace splits for 1-N split case */
/* make new guids and keep track of them */
update mintmatch
set cat_split_guid = replace(uuid(), '-', '')
where cat_split_guid is null;

delete from splits where guid in (
select distinct guid from (
/* What to delete? */
select sp.guid, tx.post_date
     , mm.original_description, ofx_acct.name ofx_acct, oacct.name del_name, mm.category
     , mm.amount, sp.value_num / sp.value_denom
from mintmatch mm
join transactions tx on mm.tx_guid = tx.guid
join splits sp on sp.tx_guid = tx.guid
join accounts oacct on oacct.guid = sp.account_guid
join accounts ofx_acct on ofx_acct.guid = mm.acct_guid
join splits ofx_split
  on ofx_split.tx_guid = tx.guid
 and ofx_split.guid != sp.guid
 and ofx_split.account_guid = ofx_acct.guid
where mm.split_qty > 1
order by mm.post_date
) old_splits );

insert into splits
select mm.cat_split_guid guid
     , mm.tx_guid
     , mm.cat_guid account_guid
     , mx.notes memo
     , '' action
     , 'n' reconcile_state
     , null reconcile_date
     , mm.amount * -100 value_num
     , 100 value_denom
     , mm.amount * -100 quantity_num
     , 100 quantity_denom
     , null lot_guid
--   , mx.date, mm.post_date, mx.description,mx.category, mx.account_name
from mintmatch mm
join mintexport mx on mx.id = mm.mint_id
where mm.split_qty > 1
order by mm.post_date;

/*

select * from accounts where guid = '9e210d4a31ac11e19236001921c7b860';
select * from accounts where guid = '9e21242e31ac11e19236001921c7b860';

income splits have negative amounts
select * from splits where account_guid = '9e210d4a31ac11e19236001921c7b860';
select * from splits where account_guid = '9e21242e31ac11e19236001921c7b860';
*/

select * from slots
-- join transactions tx on tx.guid = slots.obj_guid
join splits obj on obj.guid = slots.obj_guid
where name='online_id';

/* Fix credit card transfers */
update
-- select tx.post_date, tx.description, s.value_num from
splits s
join accounts ccp
  on s.account_guid = ccp.guid
 and ccp.name = 'Credit Card Payment'
join transactions tx on s.tx_guid = tx.guid
join accounts cc
  on cc.name = case
     when tx.description like '%American Express' then 'Costco TrueEarnings Card'
     when tx.description like '%Discover%' then 'Discover'
     when tx.description like '%Home Depot%' then 'Home Depot CC'
     end
-- order by tx.post_date
set s.account_guid = cc.guid
;

/* reproduce mint export
select date_format(date '2010-07-26', '%m/%d/%Y');
select round(13.6700, 2);
 */

create or replace view mint_re_export as
select date_format(
       -- wierd... mint dates are off by 1 and then they're not.
       case when tx.post_date < date '2011-04-20'
       then date_add(tx.post_date, interval - 1 day)
       else tx.post_date end, '%c/%d/%Y') as date
     , tx.description
     , sp0.memo as original_description
     , round(abs(sp.value_num / sp.value_denom), 2) amount
     , case when sp.value_num > 0 then 'debit' else 'credit' end as transaction_type
     , cat.name as category
     , accounts.name as account_name
     , case when sp0.reconcile_state = 'y' then 'Audited' else '' end labels -- TODO
     , sp.memo notes
     , tx.post_date
     , tx.guid as tx_guid
     , sp0.guid as main_split_guid
     , sp.guid as cat_split_guid
     , mm.mint_id -- for ordering
from transactions tx
join slots ofx on ofx.obj_guid = tx.guid and ofx.name = 'notes'
join splits sp on sp.tx_guid = tx.guid
join accounts cat on sp.account_guid = cat.guid
join splits sp0 on sp0.tx_guid = tx.guid
 and sp0.memo = substring_index(ofx.string_val, 'Memo:', -1)
 and sp0.guid != sp.guid
join slots ofx_id on ofx_id.name = 'online_id'
 and ofx_id.obj_guid = sp0.guid
join accounts on accounts.guid = sp0.account_guid
left join mintmatch mm on mm.cat_split_guid = sp.guid;

select * from mint_re_export
order by to_days(post_date) desc, mint_id;

select date, description, original_description
     , amount, transaction_type, category, account_name
-- TODO: labels, notes
from mint_re_export
order by to_days(post_date) desc, mint_id
limit 100000
into outfile '/home/connolly/qtrx/dm93finance/mint_re_export.csv'
fields terminated by ',' enclosed by '"'
;
