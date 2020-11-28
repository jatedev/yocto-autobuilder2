/*
 * decaffeinate suggestions:
 * DS002: Fix invalid constructor
 * Full docs: https://github.com/decaffeinate/decaffeinate/blob/master/docs/suggestions.md
 */
class Yoctochangedetails {
    constructor() {
        return {
            replace: true,
            restrict: 'E',
            scope: {
                change: '=',
                compact: '=?'
            },
            template: require('./yoctochangedetails.tpl.jade')
        };
    }
}

angular.module('yocto_console_view')
.directive('yoctochangedetails', [Yoctochangedetails])
