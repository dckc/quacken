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

drop table if exists mintmatch;

/* match by date, memo, amount */
create table mintmatch as
select tx.post_date
  , mx.original_description
  , (mx.amount * case when mx.transaction_type = 'debit' then -1 else 1 end) amount
  , mx.category
  , acct.name acct_name
  , sp.guid as ofx_split_guid
  , mx.id as mint_id
  , case when mx.category is null then '12345678901234567890123456789012' else null end as cat_guid
  , case when mx.category is null then '12345678901234567890123456789012' else null end as cat_split_guid
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
  and sp.value_num = sp.value_denom * (mx.amount * case when mx.transaction_type = 'debit' then -1 else 1 end)
join accounts acct
  on acct.guid = sp.account_guid
 and acct.name = mx.account_name
order by 1;

-- TODO: fix 'Dave &amp; Buster''s'
-- TODO: update tx.description using full ofx memo

/* match splits */
insert into mintmatch
        select tx.post_date
             , mtx.original_description
             , (mtx.amount * case when mtx.transaction_type = 'debit' then -1 else 1 end) amount
             , mtx.category
             , ms.account_name acct_name
             , sp.guid ofx_split_guid
             , mtx.id mint_id
             , null cat_guid
             , null cat_split_guid
        from (
          select count(*), mtx.date, mtx.account_name, mtx.original_description, sum(mtx.amount) tot
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
order by post_date;

select count(*), name
from accounts
group by name
having count(*) > 1
order by name;

SET SQL_SAFE_UPDATES=0;
update mintmatch mm
set mm.cat_guid = (
select guid from accounts cat
where cat.name = mm.category);

select * from mintmatch where cat_guid is null;

/* fill in cat_split_guid for the 1-1 (non-split) case. */
update mintmatch mm
join splits osp on osp.guid = mm.ofx_split_guid
join transactions tx on tx.guid = osp.tx_guid
join splits sp
  on sp.tx_guid = tx.guid
 and sp.guid != osp.guid
 and sp.value_num = sp.value_denom * mm.amount * -1
join accounts cat on sp.account_guid = cat.guid
set mm.cat_split_guid = sp.guid;

/* which mint transactions matched more than one gnucash trx? */
select mx.id, mx.date, mx.description, mx.amount
     , osp.value_num / osp.value_denom as ofx_split_amount
     , mm.*
from mintexport mx
join (
select count(*) qty, mint_id, ofx_split_guid
from mintmatch
group by mint_id
having count(*) > 1
order by 1 desc) dups
 on dups.mint_id = mx.id
join mintmatch mm on mm.mint_id = mx.id
join splits osp on mm.ofx_split_guid = osp.guid
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
join mintmatch mm on mm.cat_split_guid = cat_split.guid;

/* And now the moment we've all been waiting for... */
update splits cat_split
join mintmatch mm on mm.cat_split_guid = cat_split.guid
set cat_split.account_guid = mm.cat_guid;
