# Register new module
class App extends App
    constructor: ->
        return [
            'ui.router'
            'ui.bootstrap'
            'ngAnimate'
            'guanlecoja.ui'
            'bbData'
        ]

class State extends Config
    constructor: ($stateProvider, glMenuServiceProvider, bbSettingsServiceProvider) ->

        # Name of the state
        name = 'console'

        # Menu configuration
        glMenuServiceProvider.addGroup
            name: name
            caption: 'Yocto Console View'
            icon: 'exclamation-circle'
            order: 5

        # Configuration
        cfg =
            group: name
            caption: 'Yocto Console View'

        # Register new state
        state =
            controller: "#{name}Controller"
            controllerAs: "c"
            templateUrl: "yocto_console_view/views/#{name}.html"
            name: name
            url: "/#{name}"
            data: cfg

        $stateProvider.state(state)

        bbSettingsServiceProvider.addSettingsGroup
            name: 'Console'
            caption: 'Console related settings'
            items: [
                type: 'integer'
                name: 'buildLimit'
                caption: 'Number of builds to fetch'
                default_value: 200
            ,
                type: 'integer'
                name: 'changeLimit'
                caption: 'Number of changes to fetch'
                default_value: 30
            ]

class Console extends Controller
    constructor: (@$scope, $q, @$window, dataService, bbSettingsService, resultsService,
        @$uibModal, @$timeout) ->
        angular.extend this, resultsService
        settings = bbSettingsService.getSettingsGroup('Console')
        @buildLimit = settings.buildLimit.value
        @changeLimit = settings.changeLimit.value
        @dataAccessor = dataService.open().closeOnDestroy(@$scope)
        @_infoIsExpanded = {}
        @$scope.all_builders = @all_builders = @dataAccessor.getBuilders()
        @$scope.builders = @builders = []
        if Intl?
            collator = new Intl.Collator(undefined, {numeric: true, sensitivity: 'base'})
            @strcompare = collator.compare
        else
            @strcompare = (a, b) ->
                if a < b
                    return -1
                if a == b
                    return 0
                return 1

        @$scope.maping = @maping = {}

        @$scope.builds = @builds = @dataAccessor.getBuilds
            property: ["yp_build_revision", "yp_build_branch", "reason"]
            limit: @buildLimit
            order: '-started_at'
        @changes = @dataAccessor.getChanges({limit: @changeLimit, order: '-changeid'})
        @buildrequests = @dataAccessor.getBuildrequests({limit: @buildLimit, order: '-submitted_at'})
        @buildsets = @dataAccessor.getBuildsets({limit: @buildLimit, order: '-submitted_at'})

        @builds.onChange = @changes.onChange = @buildrequests.onChange = @buildsets.onChange = @onChange

        @builds.onNew = (build) =>
            build.getProperties().onChange = (properties) =>
                buildid = properties.endpoint.split('/')[1]
                if ! @maping[buildid]
                    rev = @getBuildProperty(properties[0], 'yp_build_revision')
                    if rev?
                        @maping[buildid] = rev
                        if not @onchange_debounce?
                            @onchange_debounce = @$timeout(@_onChange, 100)

    getBuildProperty: (properties, property) ->
        hasProperty = properties && properties.hasOwnProperty(property)
        return  if hasProperty then properties[property][0] else null

    onChange: (s) =>
        # if there is no data, no need to try and build something.
        if @builds.length == 0 or @all_builders.length == 0 or not @changes.$resolved or
                @buildsets.length == 0 or @buildrequests == 0
            return
        if not @onchange_debounce?
            @onchange_debounce = @$timeout(@_onChange, 100)

    _onChange: =>
        @onchange_debounce = undefined
        # we only display builders who actually have builds
        for build in @builds
            @all_builders.get(build.builderid).hasBuild = true

        @sortBuildersByTags(@all_builders)

        @changesBySSID = {}
        @changesByRevision = {}
        for change in @changes
            @changesBySSID[change.sourcestamp.ssid] = change
            @changesByRevision[change.revision] = change
            @populateChange(change)


        for build in @builds
            @matchBuildWithChange(build)

        @filtered_changes = []
        for ssid, change of @changesBySSID
            if change.comments
                change.subject = change.comments.split("\n")[0]
            for builder in change.builders
                if builder.builds.length > 0
                    @filtered_changes.push(change)
                    break
    ###
    # Sort builders by tags
    # Buildbot eight has the category option, but it was only limited to one category per builder,
    # which make it easy to sort by category
    # Here, we have multiple tags per builder, we need to try to group builders with same tags together
    # The algorithm is rather twisted. It is a first try at the concept of grouping builders by tags..
    ###

    sortBuildersByTags: (all_builders) ->
        # first we only want builders with builds
        builders_with_builds = []
        builderids_with_builds = ""
        for builder in all_builders
            if builder.hasBuild
                builders_with_builds.push(builder)
                builderids_with_builds += "." + builder.builderid

        if builderids_with_builds == @last_builderids_with_builds
            # don't recalculate if it hasn't changed!
            return
        # we call recursive function, which finds non-overlapping groups
        tag_line = @_sortBuildersByTags(builders_with_builds)
        # we get a tree of builders grouped by tags
        # we now need to flatten the tree, in order to build several lines of tags
        # (each line is representing a depth in the tag tree)
        # we walk the tree left to right and build the list of builders in the tree order, and the tag_lines
        # in the tree, there are groups of remaining builders, which could not be grouped together,
        # those have the empty tag ''
        tag_lines = []

        sorted_builders = []
        set_tag_line = (depth, tag, colspan) ->
            # we build the tag lines by using a sparse array
            _tag_line = tag_lines[depth]
            if not _tag_line?
                # initialize the sparse array
                _tag_line = tag_lines[depth] = []
            else
                # if we were already initialized, look at the last tag if this is the same
                # we merge the two entries
                last_tag = _tag_line[_tag_line.length - 1]
                if last_tag.tag == tag
                    last_tag.colspan += colspan
                    return
            _tag_line.push(tag: tag, colspan: colspan)
        self = @
        # recursive tree walking
        walk_tree = (tag, depth) ->
            set_tag_line(depth, tag.tag, tag.builders.length)
            if not tag.tag_line? or tag.tag_line.length == 0
                # this is the leaf of the tree, sort by buildername, and add them to the
                # list of sorted builders
                tag.builders.sort (a, b) -> self.strcompare(a.name, b.name)
                sorted_builders = sorted_builders.concat(tag.builders)
                for i in [1..100]  # set the remaining depth of the tree to the same colspan
                                   # (we hardcode the maximum depth for now :/ )
                    set_tag_line(depth + i, '', tag.builders.length)
                return
            for _tag in tag.tag_line
                walk_tree(_tag, depth + 1)

        for tag in tag_line
            walk_tree(tag, 0)

        @builders = sorted_builders
        @tag_lines = []
        # make a new array to avoid it to be sparse, and to remove lines filled with null tags
        for tag_line in tag_lines
            if not (tag_line.length == 1 and tag_line[0].tag == "")
                @tag_lines.push(tag_line)
        @last_builderids_with_builds = builderids_with_builds
    ###
    # recursive function which sorts the builders by tags
    # call recursively with groups of builders smaller and smaller
    ###
    _sortBuildersByTags: (all_builders) ->

        # first find out how many builders there is by tags in that group
        builders_by_tags = {}
        for builder in all_builders
            if builder.tags?
                for tag in builder.tags
                    if not builders_by_tags[tag]?
                        builders_by_tags[tag] = []
                    builders_by_tags[tag].push(builder)
        tags = []
        for tag, builders of builders_by_tags
            # we don't want the tags that are on all the builders
            if builders.length < all_builders.length
                tags.push(tag: tag, builders: builders)

        # sort the tags to first look at tags with the larger number of builders
        # @FIXME maybe this is not the best method to find the best groups
        tags.sort (a, b) -> b.builders.length - a.builders.length

        tag_line = []
        chosen_builderids = {}
        # pick the tags one by one, by making sure we make non-overalaping groups
        for tag in tags
            excluded = false
            for builder in tag.builders
                if chosen_builderids.hasOwnProperty(builder.builderid)
                    excluded = true
                    break
            if not excluded
                for builder in tag.builders
                    chosen_builderids[builder.builderid] = tag.tag
                tag_line.push(tag)

        # some builders do not have tags, we put them in another group
        remaining_builders = []
        for builder in all_builders
            if not chosen_builderids.hasOwnProperty(builder.builderid)
                remaining_builders.push(builder)

        if remaining_builders.length
            tag_line.push(tag: "", builders: remaining_builders)

        # if there is more than one tag in this line, we need to recurse
        if tag_line.length > 1
            for tag in tag_line
                tag.tag_line = @_sortBuildersByTags(tag.builders)
        return tag_line

    ###
    # fill a change with a list of builders
    ###
    populateChange: (change) ->
        change.builders = []
        change.buildersById = {}
        for builder in @builders
            builder = builderid: builder.builderid, name: builder.name, builds: []
            change.builders.push(builder)
            change.buildersById[builder.builderid] = builder
    ###
    # Match builds with a change
    ###
    matchBuildWithChange: (build) =>
        buildrequest = @buildrequests.get(build.buildrequestid)
        if not buildrequest?
            return
        buildset = @buildsets.get(buildrequest.buildsetid)
        if not buildset?
            return
        if  buildset? and buildset.sourcestamps?
            for sourcestamp in buildset.sourcestamps
                change = @changesBySSID[sourcestamp.ssid]

        if build.properties?.yp_build_revision? or @maping[build.buildid]
            if build.properties?.yp_build_revision?
                rev = build.properties.yp_build_revision[0]
            else
                rev = @maping[build.buildid]
            change = @changesByRevision[rev]
            if not change?
                change = @changesBySSID[rev]
            if not change?
                change = @makeFakeChange(rev, build.started_at, rev)
            if buildset? and buildset.parent_buildid?
                oldrev = "Unresolved #{buildset.parent_buildid}"
                delete @changesBySSID[oldrev]
            oldrev = "Unresolved #{build.builderid}-#{build.buildid}"
            delete @changesBySSID[oldrev]

            change.caption = "Commit"
            if build.properties?.yp_build_branch?
                change.caption = build.properties.yp_build_branch[0]
            change.revlink = "http://git.yoctoproject.org/cgit.cgi/poky/commit/?id=" + rev
            change.errorlink = "http://errors.yoctoproject.org/Errors/Latest/?filter=" + rev + "&type=commit&limit=150"
            if build.properties?.reason?
                change.reason = build.properties.reason[0]
        else
            if buildset? and buildset.parent_buildid?
                rev = "Unresolved #{buildset.parent_buildid}"
                if not change?
                    change = @changesBySSID[rev]
                if not change?
                    oldrev = "Unresolved #{build.builderid}-#{build.buildid}"
                    delete @changesBySSID[oldrev]
                    change = @makeFakeChange(rev, build.started_at, rev)
            if not change?
                rev = "Unresolved #{build.builderid}-#{build.buildid}"
                if not change?
                    change = @changesBySSID[rev]
                if not change?
                    change = @makeFakeChange(rev, build.started_at, rev)
            change.caption = rev

        change.buildersById[build.builderid].builds.push(build)

    makeFakeChange: (revision, when_timestamp, comments) =>
        change =
            revision: revision
            changeid: revision
            when_timestamp: when_timestamp
            comments: comments
        @changesBySSID[revision] = change
        @populateChange(change)
        return change
    ###
    # Open all change row information
    ###
    openAll: ->
        for change in @filtered_changes
            change.show_details = true

    ###
    # Close all change row information
    ###
    closeAll: ->
        for change in @filtered_changes
            change.show_details = false

    ###
    # Calculate row header (aka first column) width
    # depending if we display commit comment, we reserve more space
    ###
    getRowHeaderWidth: ->
        if @hasExpanded()
            return 400  # magic value enough to hold 78 characters lines
        else
            return 200
    ###
    # Calculate col header (aka first row) height
    # It depends on the length of the longest builder
    ###
    getColHeaderHeight: ->
        max_buildername = 0
        for builder in @builders
            max_buildername = Math.max(builder.name.length, max_buildername)
        return Math.max(100, max_buildername * 3)

    ###
    #
    # Determine if we use a 100% width table or if we allow horizontal scrollbar
    # depending on number of builders, and size of window, we need a fixed column size or a 100% width table
    #
    ###
    isBigTable: ->
        padding = @getRowHeaderWidth()
        if ((@$window.innerWidth - padding) / @builders.length) < 40
            return true
        return false
    ###
    #
    # do we have at least one change expanded?
    #
    ###
    hasExpanded: ->
        for change in @changes
            if @infoIsExpanded(change)
                return true
        return false

    ###
    #
    # display build details
    #
    ###
    selectBuild: (build) ->
        modal = @$uibModal.open
            templateUrl: 'yocto_console_view/views/modal.html'
            controller: 'consoleModalController as modal'
            windowClass: 'modal-big'
            resolve:
                selectedBuild: -> build

    ###
    #
    # toggle display of additional info for that change
    #
    ###
    toggleInfo: (change) ->
        change.show_details = !change.show_details
    infoIsExpanded: (change) ->
        return change.show_details
