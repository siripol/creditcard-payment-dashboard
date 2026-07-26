/* ============================================================================
 * recurring_rule.js  —  "ร้านค้าประจำ" (recurring merchant) rule HOOK
 * ----------------------------------------------------------------------------
 * This is the ONLY file you edit to change what counts as a recurring merchant.
 * The main code (index.html / build_data.py) is never touched.
 *
 * HOW TO CHANGE THE RULE
 *   Describe the rule you want to Claude in plain words, e.g.
 *     "ร้านที่จ่ายติดกันอย่างน้อย 4 เดือน หรือใช้เกิน 5 ครั้งรวม"
 *     "any merchant used in 6+ different months"
 *     "paid every month with total over 5000"
 *   Claude rewrites the body of isRecurring() below. That's it.
 *
 * CONTRACT
 *   window.CCRULE(m) must return true when the merchant `m` counts as recurring.
 *   If this file is missing, or CCRULE is not a function, the dashboard falls
 *   back to the built-in default (same as the default body below).
 *
 * INPUT  m = {
 *   name       : string   // merchant name
 *   cat        : string   // category key (e.g. "Insurance", "Food & Dining")
 *   total      : number   // total amount across the filtered range
 *   n          : number   // total transaction count
 *   months     : object   // { "YYYY-MM": amountThatMonth, ... }
 *   monthList  : string[] // sorted list of "YYYY-MM" the merchant appears in
 *   mCount     : number   // number of distinct months (monthList.length)
 *   maxRun     : number   // longest run of CONSECUTIVE months
 *   multi      : number   // number of months that had MORE THAN ONE transaction
 * }
 *   (Insurance is already excluded before this runs, so you don't have to.)
 * ==========================================================================*/
window.CCRULE = function isRecurring(m){
  // DEFAULT: paid in >=3 consecutive months, OR >=3 months with more than one transaction.
  return m.maxRun >= 3 || m.multi >= 3;
};
