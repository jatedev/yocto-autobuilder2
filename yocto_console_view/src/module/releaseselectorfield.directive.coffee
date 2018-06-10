
class Releaseselectorfield extends Directive
    constructor: ->
        return {
            replace: false
            restrict: 'E'
            scope: false
            templateUrl: "yocto_console_view/views/releaseselectorfield.html"
            controller: '_ReleaseselectorfieldController'
        }

class _Releaseselectorfield extends Controller
    constructor: ($scope, $http) ->
        # HACK: we find the rootfield by doing $scope.$parent.$parent
        rootfield = $scope
        while rootfield? and not rootfield.rootfield?
            rootfield = rootfield.$parent

        if not rootfield?
            console.log "rootfield not found!?!?"
            return

        # copy paste of code in forcedialog, which flatten the fields to be able to find easily
        fields_ref = {}
        gatherFields = (fields) ->
            for field in fields
                if field.fields?
                    gatherFields(field.fields)
                else
                    fields_ref[field.fullName] = field

        gatherFields(rootfield.rootfield.fields)

        console.log fields_ref

        # when our field change, we update the fields that we are suppose to
        $scope.$watch "field.value", (n, o) ->

            selector = $scope.field.selectors[n]
            if selector?
                for k, v of selector
                    console.log k
                    fields_ref[k].value = v
