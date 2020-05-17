/**
 * Module dealing with periods.
 *
 * Periods are a generalization of seasons, so another
 * way of saying this would be the "period of the year"
 * for which you are taking the average.
 *
 * For example a measurement of "tavg" and a period of
 * "12_01_02" would mean the user is asking for the
 * average temperature for December, January, and February
 * AKA Winter in the northern hemisphere and Summer in the
 * souther hemisphere.
 */
/**
 * Returns an English description of the specified period.
 */
export function getPeriodLabel(period)
{
    switch (period) {
        case 'year':
            return 'Year-round';
        case '12_01_02':
            return 'Dec-Feb';
        case '03_04_05':
            return 'Mar-May';
        case '06_07_08':
            return 'Jun-Aug';
        case '09_10_11':
            return 'Sep-Nov';
        default:
            throw new Error('Unrecognized period: ' + period);
    }
}

