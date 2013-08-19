select b.name budget_name, a.account_type, p.name parent,
    sum(amount_num / 100.0) subtot
    from budgets b
    join budget_amounts ba on ba.budget_guid = b.guid
    join accounts a on a.guid = ba.account_guid
    join accounts p on a.parent_guid = p.guid
    where b.name in ('2013 Q2')
    group by b.name, a.account_type, p.name
    ;
select b.name budget_name, a.account_type, p.name parent, a.name,
    ba.amount_num / ba.amount_denom
    from budgets b
    join budget_amounts ba on ba.budget_guid = b.guid
    join accounts a on a.guid = ba.account_guid
    join accounts p on a.parent_guid = p.guid
    where b.name in ('2013 Q2')
    order by budget_name, a.account_type, p.name, a.name
;

select * from gdocs_budget;
    
SET sql_safe_updates=0;

-- see also budget_sync.py
create table budget_import (
budget_name varchar(80),
t_log varchar(20),
account_type varchar(60),
code varchar(40),
parent varchar(80),
name varchar(80),
budget varchar(20),
notes varchar(200)
);

delete from budget_import;

load data infile '/home/connolly/qtrx/dm93finance/monthly-budget - 2003 H1.csv'
into table budget_import
COLUMNS TERMINATED BY ','
OPTIONALLY ENCLOSED BY '"'
ESCAPED BY '"'
LINES TERMINATED BY '\n'
IGNORE 1 LINES;

select * from budget_import;


select * -- distinct bi.t_lo, bi.code, bi.name
from (
 select bi.*, STR_TO_DATE(bi.t_lo,'%m/%d/%Y') d_lo
 from budget_import bi ) bi
left join budgets b
on b.name=bi.budget_name
left join accounts a
on a.code=bi.code
where bi.code > ''
-- and b.guid is null
order by bi.budget_name, bi.code, t_lo
;
select * from budget_amounts;

/* *************** */
drop table if exists acct_ancestors;

create table acct_ancestors as
select a0.guid a0guid, a1.guid a1guid, a2.guid a2guid, a3.guid a3guid, a4.guid a4guid,
 concat(
 coalesce(concat(a4.name, ':'), ''),
 coalesce(concat(a3.name, ':'), ''),
 coalesce(concat(a2.name, ':'), ''),
 coalesce(concat(a1.name, ':'), ''),
 a0.name) path,
 coalesce(a4.code, a3.code, a2.code, a1.code, a0.code) code,
 coalesce(a4.account_type, a3.account_type, a2.account_type, a1.account_type, a0.account_type) account_type
from accounts a0
join books on books.root_account_guid is not null     
left join accounts a1
  on a0.parent_guid = a1.guid
 and a1.guid != books.root_account_guid
left join accounts a2
  on a1.parent_guid = a2.guid
 and a2.guid != books.root_account_guid
left join accounts a3
  on a2.parent_guid = a3.guid
 and a3.guid != books.root_account_guid
left join accounts a4
  on a3.parent_guid = a4.guid
 and a4.guid != books.root_account_guid
;

select aa.* 
from acct_ancestors aa;

drop table if exists account_closure;
create table account_closure
as
select guid, parent_guid
from (
select a0guid guid, a0guid parent_guid
from acct_ancestors
union all
select a0guid guid, a1guid parent_guid
from acct_ancestors
union all
select a0guid guid, a2guid parent_guid
from acct_ancestors
union all
select a0guid guid, a3guid parent_guid
from acct_ancestors
union all
select a0guid guid, a4guid parent_guid
from acct_ancestors) t
where t.parent_guid is not null
;
select * from account_closure;

select ac.*, aa.*, ch.name
from account_closure ac
join acct_ancestors aa
  on aa.a0guid = ac.parent_guid
join accounts ch
  on ch.guid = ac.guid
order by aa.path;

;;;;
create or replace view budget_accts
as
select
  b.name budget_name,
  r.recurrence_period_type,
  (r.recurrence_period_start
    + interval ba.period_num month) as t_lo,
/*  (r.recurrence_period_start
    + interval ba.period_num + 1 month) as t_hi,
*/
  a.guid account_guid,
  a.account_type,
  a.code,
  pa.name parent,
  a.name,
  round(ba.amount_num / ba.amount_denom, 2) budget
from
budget_amounts ba
join budgets b on b.guid = ba.budget_guid
join accounts a on ba.account_guid = a.guid
join accounts pa on a.parent_guid = pa.guid
join recurrences r
  on b.guid = r.obj_guid
;
select * from budget_accts;

select sum(amount), account_type from (
select budget_name, t_lo, account_type, code, parent, name,
case when account_type = 'EXPENSE' then -budget
else budget end amount from budget_accts
where budget_name in ('2013 Q2')
-- and recurrence_period_type = 'month'
order by code, t_lo, name
) t2
group by account_type
;

select *
from acct_ancestors aa1
join acct_ancestors aa2
where aa2.path like (concat(aa1.path, '_%')) 
-- and aa2.code = '1203'
and aa1.account_type != 'ROOT'
and aa2.account_type != 'ROOT';

select account_type, recurrence_period_type, sum(budget)
from
(select account_type, budget, recurrence_period_type
from budget_accts
where budget_name = '2012 Q1'
) t
group by account_type, recurrence_period_type
;

select * from accounts;


select budget.parent_guid, budget.y, budget.q,
       budget.code, budget.path,
       budget, actual
/*
TODO: income/expense to cashflow
       (budget.budget * if(budget.account_type in ('EXPENSE'), -1, 1)) budget,
       (coalesce(actual.actual, 0) * if(budget.account_type in ('INCOME', 'EXPENSE', 'ASSET'), -1, 1)) actual
*/
from
(
select ac.parent_guid, budget.y, budget.q,
       aa.account_type, aa.code, aa.path,
       sum(budget.budget) budget
from
(
select
  year (r.recurrence_period_start
    + interval ba.period_num month) as y,
  quarter (r.recurrence_period_start
    + interval ba.period_num month) as q,
  ba.account_guid,
  ba.amount_num / ba.amount_denom budget
from
budget_amounts ba
join budgets b on b.guid = ba.budget_guid
join recurrences r
  on b.guid = r.obj_guid
where b.name = '2012 H1'
and r.recurrence_period_type = 'month'
) budget
join account_closure ac
  on ac.guid = budget.account_guid
join acct_ancestors aa
  on aa.a0guid = ac.parent_guid
group by budget.y, budget.q, ac.parent_guid
)
budget
left join
 (
select ac.parent_guid, actual.y, actual.q, aa.path, sum(actual.actual) actual 
from
(
select year(tx.post_date) y, quarter(tx.post_date) q,
       s.account_guid,
       sum(s.value_num / s.value_denom) actual
from splits s
join transactions tx
  on s.tx_guid = tx.guid
and tx.post_date >= (
  select r.recurrence_period_start
  from budgets b
  join recurrences r
    on b.guid = r.obj_guid
  where b.name = '2012 H1')
group by year(tx.post_date), quarter(tx.post_date), s.account_guid
) actual
join account_closure ac
  on ac.guid = actual.account_guid
join acct_ancestors aa
  on aa.a0guid = ac.parent_guid
group by actual.y, actual.q, ac.parent_guid
)
actual
on budget.parent_guid = actual.parent_guid
and budget.y = actual.y
and budget.q = actual.q
order by
 budget.code, budget.path, budget.y, budget.q
;

select if(account_type in ('INCOME'), -1, 1)
from (
select 'INCOME' account_type
union all
select 'EXPENSE' account_type
) td
;

select a1.account_type, a1.name,
       a2.account_type, a2.name,
       a3.account_type, a3.name,
       a4.account_type, a4.name
from accounts a0
left join accounts a1
  on a1.parent_guid = a0.guid
left join accounts a2
  on a2.parent_guid = a1.guid
left join accounts a3
  on a3.parent_guid = a2.guid
left join accounts a4
  on a4.parent_guid = a3.guid
where a0.guid = (select root_account_guid from books)
;

select
concat(case when a4.name = 'Root Account' then '' else concat(a4.name, ':') end, 'abc')
from (select 'xyz' as name
union all
select 'Root Account'
union all
select null) a4;

select a.guid, a.account_type,
       concat(
	case when a4.name is null or a4.name = 'Root Account' then '' else concat(a4.name, ':') end,
	case when a3.name is null or a3.name = 'Root Account' then '' else concat(a3.name, ':') end,
	case when a2.name is null or a2.name = 'Root Account' then '' else concat(a2.name, ':') end,
	case when a1.name is null or a1.name = 'Root Account' then '' else concat(a1.name, ':') end) as path,
       a.name
from accounts a
left join accounts a1
  on a.parent_guid = a1.guid
left join accounts a2
  on a1.parent_guid = a2.guid
left join accounts a3
  on a2.parent_guid = a3.guid
left join accounts a4
  on a3.parent_guid = a4.guid
;

  
;;;;;;;;;;;;;;;;;;
SELECT * FROM `dm93finance`.`accounts`;

select count(*) from mint_gc_matches;

select * from accounts
where hidden=1
;

select * from tx_split_detail td
order by td.post_date desc, td.tx_guid, td.split_guid;

select * from budgets;
select a.account_type, a.name, period_num, round(amount_num / amount_denom, 2) amount
     , ba.* from budget_amounts ba
join budgets b on b.guid = ba.budget_guid
join accounts a on ba.account_guid = a.guid
order by a.account_type desc, a.name, period_num;

select * from budget_amounts;

delete ba
-- select *
from budget_amounts ba
join budgets b on b.guid = ba.budget_guid
where b.name='2012 H1';

delete b from budgets b where b.name='2012 H1';

select * from gdocs_budget
where parent = 'EB';

select budget_name, account_type, parent, sum(amount_num / 100.0) subtot
from gdocs_budget bi
where bi.code > ''
  and budget_name in ('2013 Q2')
group by budget_name, account_type, parent
;

drop table if exists budget_decisions;
create table budget_decisions as
select a.account_type, cat, subcat
     , case
       when bd.style = 'ALL' then 'ALL'
       when qty = 1 and gp.mstart = gp.mend then 'ONE'
       else 'TWO' end as periods
     , bd.*, gp.mstart, gp.mend
from (
select count(*) qty, acct_id, style, amount
from (select acct_id
      , case when period is null then 'ALL'
        else 'SOME' end style
      , amount
 from gdocs_budget) bd
group by acct_id, style, amount) bd
join (select distinct cat, subcat, acct_id from gdocs_budget) ga
on ga.acct_id = bd.acct_id
left join (select acct_id, amount, min(period) mstart, max(period) mend
      from gdocs_budget
      where period is not null
      group by acct_id, amount) gp
on gp.acct_id = bd.acct_id and gp.amount = bd.amount
join accounts a on a.code = bd.acct_id;
select * from budget_decisions
order by account_type desc, cat, subcat;

select * from budgets;

select bu.name, h1.period, a.name, bd.* from budget_decisions bd join
(
select 0 period union all
select 1 union all
select 2 union all
select 3 union all
select 4 union all
select 5) h1 on h1.period = case
       when bd.periods = 'ALL' then h1.period
       when qty = 1 and bd.mstart = bd.mend then bd.mstart
       when qty = 2 and h1.period in (bd.mstart, bd.mend) then h1.period
       else -1 end
join accounts a on a.code = bd.acct_id
join budgets bu on bu.name = '2012 H1' -- (select distinct budget from gdocs_budget)
-- where bd.subcat = a.name and a.account_type not in ( 'INCOME')
order by account_type desc, cat, subcat, h1.period;



-- insert into budget_amounts
select null id
     , b.guid budget_guid
     , a.guid account_guid
     , gb.period period_num
     , gb.amount * 100 amount_num
     , 100 amount_denom
from gdocs_budget gb
join budgets b on gb.budget = b.name
left join accounts a
  on a.code = gb.acct_id
;
select distinct cat, subcat, acct_id from gdocs_budget gb;

use dm93finance;
select * from accounts;


select date_add(date '2012-04-01', interval x.n month)
from (select 1 n) x;

create or replace view Monthly_Budgets as
select b.name Budget
     , a.account_type
     , case
         when a.account_type in ('INCOME', 'LIABILITY') then 1
	else -1
       end as sign
     , case
         when a.description like '%#monthly%' then 'monthly'
	 else 'occasional'
       end as periods 
	 , pa.name Parent
     , a.name Account
     , date_add(r.recurrence_period_start, interval ba.period_num month) as period
     , ba.amount_num / ba.amount_denom amount
from recurrences r
join budgets b on b.guid = r.obj_guid
join budget_amounts ba on ba.budget_guid = b.guid
join accounts a on a.guid = ba.account_guid
join accounts pa on pa.guid = a.parent_guid
where r.recurrence_period_type='month'
;

select Budget, Parent, Account, period, periods, amount*sign amount
from Monthly_Budgets
order by budget, Account, period;

select Budget, quarter(period) Quarter, sum(sign * amount) Net
from Monthly_Budgets
group by Budget, quarter(period)
order by 1, 2;

select account_type, period, periods, sum(amount) from (
select Budget, account_type, Account, amount*sign amount, period, periods
from Monthly_Budgets
where Budget = '2012 Q1'
-- and period = date '2012-01-01'
order by amount
) monthly_expenses
group by account_type, period, periods
order by account_type, period, periods;

select account_type, Account, amount*sign amount, period, periods
from Monthly_Budgets
where Budget = '2012 Q1'
-- and period = date '2012-01-01'
and account_type in ('EXPENSE', 'LIABILITY')
and periods = 'occasional'
order by period, amount
;

select * from accounts;
select * from transactions;
select * from splits;

select *
from budget_amounts ba
join accounts a
  on a.guid = ba.account_guid
join budgets b
  on b.guid = ba.budget_guid
where b.name = '2012 Q2'
order by a.name, ba.period_num
;


@@delete ba
from budget_amounts ba
join accounts a
  on a.guid = ba.account_guid
join budgets b
  on b.guid = ba.budget_guid
where b.name = 'Copy of 2012 H1'
;

select * from budget_amounts
;
insert
into budget_amounts
 (budget_guid, account_guid, period_num, amount_num, amount_denom)
select (select guid from budgets where name = '2012 Q2') bq2, ba.account_guid, ba.period_num - 3, ba.amount_num, ba.amount_denom
from budget_amounts ba
join accounts a
  on a.guid = ba.account_guid
join budgets b
  on b.guid = ba.budget_guid
where b.name = '2012 H1'
 and ba.period_num > 2
order by a.name, ba.period_num
;


-- Flat view for export
create or replace view split_detail as
select
tx.post_date,
a.code,
coalesce(
 case when s.value_num < 0
  then a.path
  else null
end, '') account_db,
coalesce(
 case when s.value_num < 0
  then s.value_num / s.value_denom
  else null
end, '') amount_db,
coalesce(
 case when s.value_num >= 0
  then a.path
  else null
end, '') account_cr,
coalesce(
 case when s.value_num > 0
  then s.value_num / s.value_denom
  else null
end, '') amount_cr,
tx.description,
s.memo,
coalesce(slots.string_val, '') online_id,
s.guid,
tx.guid tx_guid
from transactions tx
join splits s on s.tx_guid = tx.guid
join acct_ancestors a on s.account_guid = a.a0guid
left join slots on slots.obj_guid = s.guid and slots.name = 'online_id'
;

select * from split_detail
order by post_date desc, tx_guid
;


select sd.* from split_detail sd
where timestampdiff(day, sd.post_date, current_timestamp) < 120
order by post_date desc, tx_guid
;

create or replace
VIEW `split_detail` AS select `tx`.`post_date` AS `post_date`,`tx`.`description` AS `description`,(`s`.`value_num` / `s`.`value_denom`) AS `amount`,`s`.`memo` AS `memo`,`a`.`code` AS `code`,`a`.`path` AS `path`,coalesce(`slots`.`string_val`,'') AS `online_id`,`s`.`guid` AS `guid`,`tx`.`guid` AS `tx_guid` from (((`transactions` `tx` join `splits` `s` on((`s`.`tx_guid` = `tx`.`guid`))) join `acct_ancestors` `a` on((`s`.`account_guid` = `a`.`a0guid`))) left join `slots` on(((`slots`.`obj_guid` = `s`.`guid`) and (`slots`.`name` = 'online_id'))))
;
