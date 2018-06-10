class Yoctochangedetails extends Directive('common')
    constructor: ->
        return {
            replace: true
            restrict: 'E'
            scope:
                change: '='
                compact: '=?'
            templateUrl: 'yocto_console_view/views/yoctochangedetails.html'
        }
