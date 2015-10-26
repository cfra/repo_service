$(function () {
    $('#the_form').submit(function() {
	var repo_name;
        $('#message').hide();
        $('#submit')[0].disabled = true;
        $('#spinner').show();

	repo_name = this["name"].value;
        $.xmlrpc({
            url: 'api',
            methodName: 'create_repo',
            params: [
                'sublab',
                repo_name,
                this["description"].value
            ],

            success: function(response, status, jqXHR) {
                var error;

                $('#spinner').hide();
                $('#submit')[0].disabled = false;

                if (response != 'SUCCESS') {
                    error = 'Unknown error ' + response
                    if (response == 'ERROR_NAME')
                        error = 'Invalid name';
                    if (response == 'ERROR_DESC')
                        error = 'Invalid description';
                    if (response == 'ERROR_EXISTS')
                        error = 'Repository does already exist';
                    if (response == 'ERROR_GITOLIE')
                        error = 'Couldn\'t change gitolite config';
                    if (response == 'ERROR_CGIT')
                        error = 'Couldn\'t change cgit config';
                    $('#message').text('Error creating repository: '
                                       + error).show();
                    return;
                }

                $('#the_form').hide(400);
                $('#message').text('Repository created successfuly. You will'
                                   + ' be redirected shortly.').show();
		setTimeout(function() {
		    window.location.href = '/' + repo_name + '/';
		}, 3000);
            },
            error: function(jqXHR, status, error) {
                $('#message').text('Coulnd\'t create Repo: ' + error);
            }
        });
        return false;
    });
    $('#message').hide();
    $('#the_form').show();
});
