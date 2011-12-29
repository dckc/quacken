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

select acct.name, s.*
from accounts acct
join slots s on s.obj_guid = acct.guid
order by 1;

insert into slots (obj_guid, name, slot_type, string_val)
select acct.guid obj_guid
     , 'color' name
     , 4 slot_type
     , 'Not Set' string_val
from accounts parent
join accounts acct on acct.parent_guid = parent.guid
where parent.name='Mint Export';

/* Just a few dups of this sort... */
select count(*), date, original_description, transaction_type, amount
from mintexport
group by date, original_description, transaction_type, amount
having count(*) > 1
order by date desc;

drop table mintmatch;

/* match by date, memo, amount */
create table mintmatch as
select tx.post_date
  , mx.original_description
  , mx.amount
  , mx.category
  , acct.name acct_name
  , sp.guid as split_guid
  , mx.id as mint_id
  , null as cat_guid
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


/* match checks */
insert into mintmatch
select tx.post_date
  , mx.original_description
  , mx.amount
  , mx.category
  , acct.name acct_name
  , sp.guid as split_guid
  , mx.id as mint_id
  , null as cat_guid
from transactions tx
join splits sp on sp.tx_guid = tx.guid
join mintexport mx
on mx.original_description = concat('Check #', tx.num, ' #', tx.num)
join accounts acct
  on acct.guid = sp.account_guid
 and acct.name = mx.account_name
order by 1;

/* which mint transactions matched more than one gnucash trx? */
select mx.id, mx.date, mx.description, mx.amount, sp.value_num / sp.value_denom as split_amount
from mintexport mx
join (
select count(*) qty, mint_id, split_guid
from mintmatch
group by mint_id
having count(*) > 1
order by 1 desc) dups
 on dups.mint_id = mx.id
join mintmatch mm on mm.mint_id = mx.id
join splits sp on mm.split_guid = sp.guid;

/* just a few mismatches... check dates? */
select *
from mintexport mx
left join mintmatch mm on mx.id = mm.mint_id
where mm.mint_id is null
  and mx.date > date '2010-07-20'
  and mx.date <= date '2010-10-20'
  and mx.account_name = 'PERFORMANCE CHECKING'
order by mx.date;
