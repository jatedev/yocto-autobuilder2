/*
 * decaffeinate suggestions:
 * DS002: Fix invalid constructor
 * DS101: Remove unnecessary use of Array.from
 * DS102: Remove unnecessary code created because of implicit returns
 * DS205: Consider reworking code to avoid use of IIFEs
 * DS207: Consider shorter variations of null checks
 * Full docs: https://github.com/decaffeinate/decaffeinate/blob/master/docs/suggestions.md
 */

class Releaseselectorfield {
    constructor() {
        return {
            replace: false,
            restrict: 'E',
            scope: false,
            template: require('./releaseselectorfield.tpl.jade'),
            controller: '_ReleaseselectorfieldController'
        };
    }
}

class _releaseselectorfield {
    constructor($scope, $http) {
        // HACK: we find the rootfield by doing $scope.$parent.$parent
        let rootfield = $scope;
        while ((rootfield != null) && (rootfield.rootfield == null)) {
            rootfield = rootfield.$parent;
        }

        if ((rootfield == null)) {
            console.log("rootfield not found!?!?");
            return;
        }

        // copy paste of code in forcedialog, which flatten the fields to be able to find easily
        const fields_ref = {};
        var gatherFields = fields => Array.from(fields).map((field) =>
            (field.fields != null) ?
                gatherFields(field.fields)
            :
                (fields_ref[field.fullName] = field));

        gatherFields(rootfield.rootfield.fields);

        // when our field change, we update the fields that we are suppose to
        $scope.$watch("field.value", function(n, o) {

            const selector = $scope.field.selectors[n];
            if (selector != null) {
                return (() => {
                    const result = [];
                    for (let k in selector) {
                        const v = selector[k];
                        if (k in fields_ref) {
                            result.push(fields_ref[k].value = v);
                        }
                    }
                    return result;
                })();
            }
        });
    }
}

angular.module('yocto_console_view')
.directive('releaseselectorfield', [Releaseselectorfield])
.controller('_ReleaseselectorfieldController', ['$scope', '$http', _releaseselectorfield])
