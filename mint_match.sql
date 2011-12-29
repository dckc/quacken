use dm93finance;

select ma.* from
(select distinct account_name from mintexport) ma
left join accounts ga on ga.name = ma.account_name
where ga.name is null
;
select * from mintexport where account_name='Cash';

-- guid column is only 32 chars long
select length(replace(uuid(), '-', ''));

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
          , sum(amount * case when transaction_type = 'debit' then -1 else 1 end) as tot
     from mintexport
     group by category) x) mc
join commodities usd on usd.mnemonic='USD'
join accounts parent on parent.name=
   case when mc.account_type = 'EXPENSE' then 'Mint Expenses' else 'Mint Income' end
order by 3, 2;
-- 124 row(s) affected

select distinct slot_type from slots
order by 1;
select * from slots where slot_type=10;
-- 1: int64_val
-- 4: string_val
-- 5: guid_val
-- 6: timespec_val
-- 9: guid_val again?
-- 10: gdate_val

/* Just a few dups of this sort... */
select count(*), date, original_description, transaction_type, amount
from mintexport
group by date, original_description, transaction_type, amount
having count(*) > 1
order by date desc;

/* extract check numbers */
update mintexport
set num = substring_index(original_description, '#', -1)
where original_description like 'Check #%'
and id > 0;

/* Fix 'Check #7193 #7193' to 'Check #7193'*/
update mintexport
set original_description = concat('Check #', num)
where num is not null;

/* We need unique names for accounts for this work. */
create unique index accounts_name on accounts (name(250));

drop table if exists mintmatch;

/* match by date, memo, amount */
create table mintmatch as
select tx.post_date
  , mx.original_description
  , (mx.amount * case when mx.transaction_type = 'debit' then -1 else 1 end) amount
  , mx.category
  , cat.guid cat_guid
  , mx.account_name acct_name
  , accounts.guid acct_guid
  , tx.guid as tx_guid
  , mx.id as mint_id
--  , (select name from accounts where guid = sp.account_guid) cat_name
  , case when sp.guid is not null then sp.guid else null end as cat_split_guid -- nullable
  , 1 as split_qty
from transactions tx
join splits sp on sp.tx_guid = tx.guid
join
(
select obj_guid, substring_index(string_val, 'Memo:', -1) as ofx_memo
from slots
where name = 'notes') ofx on ofx.obj_guid = tx.guid
join mintexport mx
on mx.original_description = ofx.ofx_memo
  and timestampdiff(day, tx.post_date, mx.date) between -1 and 0
  and sp.value_num = sp.value_denom * (mx.amount * case when mx.transaction_type = 'credit' then -1 else 1 end)
join accounts on accounts.name = mx.account_name
join accounts cat on cat.name = mx.category
order by 1;

-- TODO: fix 'Dave &amp; Buster''s'
-- TODO: update tx.description using full ofx memo

/* match splits
delete from mintmatch
where cat_split_guid is null;
 */
insert into mintmatch
        select tx.post_date
             , mtx.original_description
             , (mtx.amount * case when mtx.transaction_type = 'debit' then -1 else 1 end) amount
             , mtx.category
             , cat.guid cat_guid
             , ms.account_name acct_name
             , accounts.guid acct_guid
             , tx.guid tx_guid
             , mtx.id mint_id
             , null cat_split_guid
             , ms.qty
        from (
          select count(*) qty, mtx.date, mtx.account_name, mtx.original_description
               , sum(mtx.amount * case when mtx.transaction_type = 'debit' then -1 else 1 end) tot
          from mintexport mtx
          group by mtx.date, mtx.account_name, mtx.original_description
          having count(*) > 1) ms

        join transactions tx on timestampdiff(day, tx.post_date, ms.date) between -5 and 5
        join splits sp on sp.tx_guid = tx.guid
         and sp.value_num = ms.tot * sp.value_denom
        join mintexport mtx
          on mtx.date = ms.date
         and mtx.account_name = ms.account_name
         and mtx.original_description = ms.original_description
        join accounts on accounts.name = mtx.account_name
        join accounts cat on cat.name = mtx.category
        where not exists (select * from mintmatch mm where mm.mint_id = mtx.id)
order by post_date;

select * from mintmatch where cat_split_guid is null;
select * from mintmatch where split_qty > 1;

select count(*), name
from accounts
group by name
having count(*) > 1
order by name;

select * from mintmatch where cat_guid is null;

/* which mint transactions matched more than one gnucash trx? */
select mx.id, mx.date, mx.description, mx.amount
     , osp.value_num / osp.value_denom as ofx_split_amount
     , mm.*
from mintexport mx
join (
select count(*) qty, mint_id, tx_guid
from mintmatch
group by mint_id
having count(*) > 1
order by 1 desc) dups
 on dups.mint_id = mx.id
join mintmatch mm on mm.mint_id = mx.id
join splits osp on mm.tx_guid = osp.tx_guid and osp.account_guid = mm.cat_guid
order by 1;

/* is it ever ambiguous? */
select count(*), mint_id from (
select distinct mint_id, mx.category
from (
select count(*) qty, mint_id
from mintmatch
group by mint_id
having count(*) > 1) dups
join mintexport mx on dups.mint_id = mx.id
) id_cat group by mint_id
having count(*) > 1;

/* just a few mismatches... check dates: */
-- BUG: DAVE & BUSTERS etc.
select q.min_post, q.max_post, timestampdiff(day, q.min_post, mx.date) diff_min, mx.*
from mintexport mx
left join mintmatch mm on mx.id = mm.mint_id
left join (
  select min(post_date) min_post, max(post_date) max_post, qs.memo
  from splits qs
  join transactions tx on qs.tx_guid = tx.guid
  group by qs.memo
  ) q
on mx.original_description = q.memo
and abs(timestampdiff(day, q.min_post, mx.date)) < 20

where mm.mint_id is null
  and mx.date > date '2010-07-20'
  and mx.date <= date '2010-10-20'
  and mx.account_name = 'PERFORMANCE CHECKING'

order by mx.date;

/* Just Imbalance-USD, at least to start. */
select distinct ocat.name
from accounts ocat
join splits cat_split on cat_split.account_guid = ocat.guid
join mintmatch mm on mm.cat_split_guid = cat_split.guid
order by 1;

/* And now the moment we've all been waiting for...
what are we about to update? */
select *
from splits cat_split
join mintmatch mm on mm.cat_split_guid = cat_split.guid
where cat_split.account_guid != mm.cat_guid;

update splits cat_split
join mintmatch mm on mm.cat_split_guid = cat_split.guid
set cat_split.account_guid = mm.cat_guid;

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

