use dm93finance;
SET sql_safe_updates=0;

/* Flag parents by counting children. */
/* Parents don't come with accounts. Fill in from children. */
update minttrx p set p.children=null;
update minttrx p
join (
  select count(*) qty, min(account) account, parent
  from minttrx
  where parent is not null
  group by parent) ea
on ea.parent = p.id
set p.children = ea.qty,
p.account = ea.account;

/* Eyeball parents and children. */
select * from minttrx
where children > 0 or isChild = 1
order by date, (case when isChild=1 then parent else id end);

/****************************
 * Accounts
 */

/* We need unique names for accounts for this work. */
create unique index accounts_name on accounts (name(250));
/* codes are unique where they're non-trivial */
create index accounts_code on accounts (code(250));

/* We assume any mint transactions whose accounts (e.g. Cash) don't match
 * existing gnucash accounts by name can be ignored. Eyeball them: */
select * from minttrx
where children is null and account in (

select ma.* from
(select distinct account from minttrx) ma
left join accounts ga on ga.name = ma.account
where ga.name is null

);

-- guid column is only 32 chars long
select length(replace(uuid(), '-', ''));

/* Now that we have the JSON category data from mint... */
drop table if exists mint_budget_categories;
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

create or replace view mint_categories as
select sub.id, sub.subcategory category
     , case super.category
       when 'Income' then 'INCOME'
       when 'Transfer' then 'ASSET'
       else 'EXPENSE'
       end as account_type
     , super.id parent, super.category parent_name
from mint_budget_categories sub
join mint_budget_categories super on sub.category=super.category
where sub.subcategory is not null
 and super.subcategory is null
union all
select id, category
     , case category
       when 'Income' then 'INCOME'
       when 'Transfer' then 'ASSET'
       else 'EXPENSE' end
     , null, null
from mint_budget_categories
where subcategory is null;

/* check transaction categoryId against budget categories */
select case when qty = 0 then 1 else 1/0 end all_trx_cats_match
from (
  select count(*) qty
  from (
    select mx.* from minttrx mx
    left join mint_categories mc
    on mx.categoryId = mc.id
  where mc.id is null) mismatches ) tally;

-- any categories that we used not in gnucash?
select mc.* from mint_categories mc
left join accounts a on a.code = mc.id
where a.code is null
and mc.id in (select distinct categoryId from minttrx) -- actually used
;


/* Set up top level accounts. */
insert into accounts
select replace(uuid(), '-', '') as guid
     , mc.category as name, mc.account_type
     , usd.guid as commodity_guid, usd.fraction as commodity_scu, 0 as non_std_scu
     , ap.guid as parent_guid
     , mc.id as code
     , '' as description, 0 as hidden, 0 as placeholder
from mint_categories mc
join accounts ap on ap.name =
  case mc.account_type
  -- we assume gnucash accounts with these names have been pre-arranged
  when 'EXPENSE' then 'Spending'
  when 'INCOME' then 'Income'
  when 'ASSET' then 'Current'
  end
join commodities usd on usd.mnemonic = 'USD'
where mc.parent is null
and mc.category not in (select name from accounts) -- not yet created
;

/* Set up 2nd level accounts. */
insert into accounts
select replace(uuid(), '-', '') as guid
     , mc.category as name, mc.account_type
     , usd.guid as commodity_guid, usd.fraction as commodity_scu, 0 as non_std_scu
     , ap.guid as parent_guid
     , mc.id as code
     , '' as description, 0 as hidden, 0 as placeholder
from mint_categories mc
join accounts ap on ap.code = mc.parent
join commodities usd on usd.mnemonic = 'USD'
and mc.id in (select distinct categoryId from minttrx) -- actually used
and mc.category not in (select name from accounts) -- not yet created
;


/* Check for pre-existing gnucash categories with matching names but mismatched codes. */
-- update
select * from
accounts a
join mint_categories mc on mc.category = a.name
where a.code != mc.id
-- set a.code = mc.id
;

select * from mint_categories mc join accounts a on mc.id = a.code
join accounts p on p.code = mc.parent
where mc.parent is not null and a.parent_guid != p.guid
and parent_name != 'Transfer' -- these are assets/liabilities, which mint doesn't really grok
and parent_name != 'Financial' -- I used ths mint expense category for things that are really assets/liabilities
and category != 'Personal Loan' -- this looked like income in mint, but clearly it's not
;


/****************************
 * Transactions
 */

create or replace view tx_split_detail as
select tx.post_date, a.name account_name, tx.description, s.memo, s.value_num / s.value_denom amount
     , tx.guid tx_guid, s.guid split_guid, a.guid account_guid, value_num
from transactions tx
join splits s on s.tx_guid = tx.guid
join accounts a on s.account_guid = a.guid;

/* Check balances */
select sum(amount), account_name
from tx_split_detail
group by name
order by name;

/* Aside: Which transactions from mint accounts don't have OFX online_id's?
 * They seem to all be transfers, which I think I messed around with manually. */
select td.*
from tx_split_detail td
left join slots on slots.obj_guid = td.split_guid and slots.name = 'online_id'
where td.account_name in (select distinct account from minttrx)
and slots.obj_guid is null;



-- alter table minttrx drop index minttrx_sig;
-- create index minttrx_sig on minttrx (account, omerchant);

/* Find various descriptions of each transaction split.
 * DEAD CODE */
create or replace view tx_desc as
select td.split_guid guid, td.tx_guid, td.post_date, td.account_guid, td.account_name account, td.value_num
     /* My bank repeats the OFX NAME in the MEMO, but Discover doesn't Ugh. */
     , td.description
     , case when td.memo > '' then td.memo else null end memo
     , case when ofxmemo.obj_guid is not null and ofxmemo.string_val like '%Memo:%'
       then substring_index(ofxmemo.string_val, 'Memo:', -1)
       else null
       end ofx_memo
from tx_split_detail td
left join slots ofxmemo on ofxmemo.obj_guid = td.tx_guid
     and ofxmemo.name = 'notes';

drop table if exists mint_gc_matches;
create table mint_gc_matches (
 guid varchar(32) not null, -- of split corresponding to account
 tx_guid varchar(32) not null,
 post_date timestamp not null,
 ddelta int not null,
 id int not null,
 children int,
 date date not null,
 account varchar(250) not null,
 description varchar(250) not null,
 amount decimal(8, 2) not null,
 categoryId int not null,
 category varchar(80) not null,
 cat_guid varchar(32) not null,
 account_guid varchar(32) not null,
 cat_split_guid varchar(32),
 txtscore int not null
);
create index mgm_id on mint_gc_matches (id);
create index mgm_guid on mint_gc_matches (guid);

/* retrofit txtscore */
update mint_gc_matches mm join (
select mx.date
     , case
       when instr(mx.omerchant, 'Check #') = 1
        and instr(ofxmemo.string_val, substr(mx.omerchant, 1, length('Check #9999'))) then 1000
       when instr(ofxmemo.string_val, mx.omerchant) > 0 then length(mx.omerchant)
       when instr(mx.omerchant, td.description) > 0 then length(td.description)
       when instr(mx.omerchant, replace(td.description, "'", '')) > 0 then length(td.description)
       else null
       end txtscore
     , mx.account, mx.omerchant, td.description, ofxmemo.string_val
     , mm.id, mm.guid
from mint_gc_matches mm
join minttrx mx on mx.id = mm.id
join tx_split_detail td on td.split_guid = mm.guid
join slots ofxmemo on ofxmemo.obj_guid = td.tx_guid
     and ofxmemo.name = 'notes'
-- order by 2
) q on mm.id = q.id and mm.guid = q.guid
set mm.txtscore = q.txtscore;

insert into mint_gc_matches (
  guid, tx_guid, post_date, ddelta, txtscore, id, children, date, account, description, amount
, categoryId, category, cat_guid, account_guid)
select * from (
select gcand.guid, gcand.tx_guid, gcand.post_date
     , timestampdiff(day, gcand.post_date, mcand.date) ddelta
     , case
       -- checks trump
       when instr(mcand.omerchant, 'Check #') = 1
        -- patch goofy Check #1234 #1234 case
        and instr(gcand.ofx_memo, substr(mcand.omerchant, 1, length('Check #9999'))) then 1000
       when instr(gcand.ofx_memo, mcand.omerchant) > 0 then length(mcand.omerchant)
       when instr(mcand.omerchant, gcand.description) > 0 then length(gcand.description)
       -- match Sam's Club to SAMS CLUB
       when instr(mcand.omerchant, replace(gcand.description, "'", '')) > 0 then length(gcand.description)
       -- try without spaces
       when instr(replace(mcand.omerchant, ' ', ''), replace(gcand.description, ' ', '')) > 0 then length(gcand.description)
       else null
       end txtscore
     , mcand.*, cat.guid cat_guid, account_guid
from (
select mx.id, mx.children, mx.date, mx.account, mx.omerchant
     , case when mx.isDebit = 1 then - mx.amount else mx.amount end amount
     , mx.categoryId, mx.category
from minttrx mx
left join mint_gc_matches done on done.id = mx.id
where mx.isChild != 1
and mx.isDuplicate = 0
and mx.category not in ('Exclude From Mint')
and done.id is null -- incremental matching
) mcand
join (
 select td.split_guid guid, td.tx_guid, td.post_date
      , td.account_guid, td.account_name account, td.value_num
      , td.description, ofxmemo.string_val ofx_memo
 from tx_split_detail td
 left join slots ofxmemo on ofxmemo.obj_guid = td.tx_guid
     and ofxmemo.name = 'notes'
 left join mint_gc_matches done on done.guid = td.split_guid
 where td.account_name in (select distinct account from minttrx)
and done.guid is null -- incremental matching
) gcand
on timestampdiff(day, gcand.post_date, mcand.date) between -12 and 10 -- mcand.date = cast(gcand.post_date as date)
and mcand.account = gcand.account
-- todo: chase down full memos
and mcand.amount * 100 = gcand.value_num
join accounts cat on cat.code = mcand.categoryId) mgmatch
where txtscore is not null;


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
on bad.guid = mm.guid and bad.id = mm.id;

/* Likewise if a mint trx matches better and worse, delete the worse match. */
delete mm from mint_gc_matches mm
join (
-- select *
select bad.guid, bad.id
from mint_gc_matches bad
join mint_gc_matches mm
  on mm.id = bad.id
and abs(mm.ddelta) < abs(bad.ddelta)) bad
on mm.id = bad.id and mm.guid = bad.guid;

-- We should be able to create this unique index, though we don't use it for anything.
-- create unique index mgc_idid on mint_gc_matches (id, guid);
-- alter table mint_gc_matches drop index mgc_idid;

/* Of the remaining dups, this shows any ambiguities in the resulting categories.
 * None. Yay. */
select qty, mx.* from (
select count(*) qty, id from (
  select distinct id, category from (
    -- This subquery lets you eyeball the few remaining dups.
    select qty, mm.id id_check, category cat_check, mm.* from (
      select count(*) qty, id
      from (select distinct id, guid from mint_gc_matches) x
      group by id
      having count(*) > 1
      order by 1 desc) dups
    join mint_gc_matches mm on dups.id = mm.id
    order by mm.id) dup_details
  ) x
group by id
having count(*) > 1) dups
join minttrx mx on mx.id = dups.id;

/* ew... where did these come from?
   Ah... found it. */
delete mm from mint_gc_matches mm
join (
select mm.*
from mint_gc_matches mm
left join minttrx mx on mm.id = mx.id
where mx.id is null
) bad on bad.id=mm.id and bad.guid=mm.guid;

-- TODO: fix 'Dave &amp; Buster''s'
-- TODO: update tx.description using full ofx memo

/* just a few mismatches... check dates: */
-- BUG: DAVE & BUSTERS etc.
select mx.*
from minttrx mx
left join mint_gc_matches mm
  on mm.id = mx.id
where mm.id is null
  and mx.isChild = 0 and mx.children is null
  -- spaces, &
  and mx.id not in ('296017984', '295931876', '298228734', '305034939', '311162603', '384319337', '384319338')
  -- beginning of my epoch
  and mx.date > date '2010-06-30'
  and mx.category not in ('Exclude From Mint')
  -- I have only reconciled one month of discover
  and not (mx.account = 'Discover' and mx.date > date '2011-12-14') -- '2010-07-14'
  and not (mx.account = 'PERFORMANCE CHECKING' and mx.date > date '2011-11-16')
  -- haven't done these
  and mx.account not in ('Costco TrueEarnings Card', 'SAVINGS', 'Home Depot CC')
  and mx.category not in ('Credit Card Payment')
order by mx.date;

/* Find the category split, provided it hasn't been refined yet. */
update mint_gc_matches mm
join splits spa on mm.guid = spa.guid
join transactions tx on spa.tx_guid = tx.guid
join splits cat_split on cat_split.tx_guid = tx.guid
 and cat_split.value_num = - spa.value_num
join accounts cat on cat_split.account_guid = cat.guid
set mm.cat_split_guid = cat_split.guid
where mm.cat_split_guid is null;
/* TODO: get post_date to hold still. */
update mint_gc_matches mm
join transactions tx on mm.tx_guid = tx.guid
set mm.post_date = tx.post_date;

/* For each matching parent, generate matches for children
   with made up cat_split_guid's. */
insert into mint_gc_matches
select mmp.guid, mmp.tx_guid, mmp.post_date, mmp.ddelta, mxch.id
     , null children, mmp.date, mmp.account, mmp.description
     , case when mxch.isDebit then -mxch.amount else mxch.amount end amount
     , mxch.categoryId, mxch.category
     , cat.guid cat_guid
     , mmp.account_guid
     , replace(uuid(), '-', '') cat_split_guid
     , mmp.txtscore
from mint_gc_matches mmp
join minttrx mxch on mxch.parent = mmp.id
join accounts cat on cat.code = mxch.categoryId
left join mint_gc_matches done on done.id = mxch.id
where done.id is null;

/* And now the moment we've all been waiting for...
what are we about to update?*/
select cat.name ocat, mm.category, mm.* from mint_gc_matches mm
join splits cat_split on mm.cat_split_guid = cat_split.guid
join accounts cat on cat.guid = cat_split.account_guid
where cat.account_type in ('CASH', 'INCOME', 'EXPENSE') -- leave transfers alone
 and cat_split.account_guid != mm.cat_guid
and mm.children is null;

update splits cat_split
join mint_gc_matches mm on mm.cat_split_guid = cat_split.guid
join minttrx mx on mm.id = mx.id
join accounts cat on cat_split.account_guid = cat.guid
set cat_split.account_guid = mm.cat_guid,
    cat_split.memo = mx.note
    -- todo: labels
where cat.account_type in ('CASH', 'INCOME', 'EXPENSE')
and mm.children is null;

/* replace splits for 1-N split case */

/*clean up from previous algorithm
delete from splits where guid in (
-- select * from tx_desc where guid in (
select q1.guid from (
select distinct spd.guid
from splits spd
join mintmatch mm on mm.cat_split_guid = spd.guid
where mm.split_qty > 1) q1);
-- 244 rows affected
*/

update splits
-- select *
join mint_gc_matches mmp on mmp.cat_split_guid = splits.guid
join minttrx mxp on mxp.id = mmp.id
set value_num = 0, quantity_num=0
where mxp.children is not null;
-- 123 rows affected

insert into splits
select mm.cat_split_guid guid
     , mm.tx_guid
     , mm.cat_guid account_guid
     , mx.note memo
     , '' action
     , 'n' reconcile_state, null reconcile_date
     , mm.amount * -100 value_num, 100 value_denom
     , mm.amount * -100 quantity_num, 100 quantity_denom
     , null lot_guid
--   , mx.date, mm.post_date, mx.description,mx.category, mx.account_name
from mint_gc_matches mm
join minttrx mx on mx.id = mm.id
left join splits done on mm.cat_split_guid = done.guid
where mx.isChild = 1
and done.guid is null
order by mm.post_date;

/* clean up leftovers from earlier split inserts. */
delete bad
-- select *
from splits bad
join mint_gc_matches mm on bad.tx_guid = mm.tx_guid
 and bad.account_guid = mm.cat_guid
 and bad.value_num = -100 * mm.amount
left join mint_gc_matches done
on done.cat_split_guid = bad.guid
where done.guid is null
;
select * from tx_split_detail td
left join mint_gc_matches mm on mm.cat_split_guid = td.split_guid
 where td.memo='tool bandit';

/*TODO: clean up transaction descriptions */
update transactions tx
join mint_gc_matches mm on mm.tx_guid = tx.guid
join minttrx mx on mm.id = mx.id
set tx.description = mx.merchant
where
-- mx.isChild = 0 and
mx.children is null;


/* TODO: undo damage from false positives from earlier algorithm*/
select * from mint_gc_matches mm
join minttrx mx on mx.id = mm.id
where mm.cat_split_guid is null
and mx.isChild = 0
and mx.children is null;


/* manual clean-up */
select * from mintexport mx
left join mintmatch mm on mm.mint_id = mx.id
where
-- mx.amount = 12.25
mx.original_description like '%CULVER%'
order by date;


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
     -- TODO: clean up descriptions?
     , case when mx.merchant is null then tx.description
       else tx.description end description
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
     , mm.id -- for ordering
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
left join mint_gc_matches mm on mm.cat_split_guid = sp.guid
left join minttrx mx on mx.id = mm.id -- kludge for descriptions for now
;

select * from mint_re_export
order by to_days(post_date) desc, mint_id;

select mx.category, mx.categoryId
from minttrx mx
left join accounts a on a.code = mx.categoryId
where a.code is null;

select date, description, original_description
     , amount, transaction_type, category, account_name
-- TODO: labels, notes
from mint_re_export
order by to_days(post_date) desc, id desc
limit 100000
into outfile '/home/connolly/qtrx/dm93finance/mint_re_export.csv'
fields terminated by ',' enclosed by '"'
;
