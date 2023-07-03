window.onscroll = function() {myFunction()};
        
var navbar = document.getElementById("navbar");
var sticky = navbar.offsetTop;

function myFunction() {
  if (window.pageYOffset >= sticky) {
    navbar.classList.add("sticky")
    navbar.classList.add("navbar-sticky")
    navbar.classList.remove("navbar-default")
  } else {
    navbar.classList.remove("sticky")
  }
}

var bar = document.getElementById('progressbar');
UIkit.upload('.js-upload', {
    url: 'upload',
    multiple: false,
    method: 'POST',
    name: 'file',
    complete: async function (res) {
        res = JSON.parse(res.response);
        if ( res.ok ) {
            await updateFileList();
            setTimeout(function () {
                bar.setAttribute('hidden', 'hidden');
                UIkit.notification({message: 'Upload Success', status: 'success'})
            }, 1000);
        } else {
            setTimeout(function () {
                bar.setAttribute('hidden', 'hidden');
                UIkit.notification({message: 'Upload Failed: ' + res.error, status: 'danger'})
            }, 1000);
        }

    },

    loadStart: function (e) {
        bar.removeAttribute('hidden');
        bar.max = e.total;
        bar.value = e.loaded;
    },

    progress: function (e) {
        bar.max = e.total;
        bar.value = e.loaded;
    },

    loadEnd: function (e) {
        bar.max = e.total;
        bar.value = e.loaded;
    },

    error: function (e) {
        console.log('error', e);
        // parse error
        res = JSON.parse(e.response);
        setTimeout(function () {
            bar.setAttribute('hidden', 'hidden');
            UIkit.notification({message: 'Upload Failed', status: 'danger'})
        }, 1000);
    }

});

UIkit.upload('.js-upload-put', {
    url: 'upload',
    multiple: false,
    method: 'PUT',
    name: 'file',
    complete: async function (res) {
        console.log('complete', JSON.parse(res.response));
        res = JSON.parse(res.response);
        if ( res.ok ) {
            await updateFileList();
            setTimeout(function () {
                bar.setAttribute('hidden', 'hidden');
                UIkit.notification({message: 'Update Success', status: 'success'})
            }, 1000);
        } else {
            setTimeout(function () {
                bar.setAttribute('hidden', 'hidden');
                UIkit.notification({message: 'Update Failed: ' + res.error, status: 'danger'})
            }, 1000);
        }

    },

    loadStart: function (e) {
        bar.removeAttribute('hidden');
        bar.max = e.total;
        bar.value = e.loaded;
    },

    progress: function (e) {
        bar.max = e.total;
        bar.value = e.loaded;
    },

    loadEnd: function (e) {
        bar.max = e.total;
        bar.value = e.loaded;
    },

    error: function (e) {
        console.log('error', e);
        // parse error
        res = JSON.parse(e.response);
        setTimeout(function () {
            bar.setAttribute('hidden', 'hidden');
            UIkit.notification({message: 'Update Failed', status: 'danger'})
        }, 1000);
    }

});


async function updateFileList() {
    let response = await fetch('file-list');
    response = await response.json();
    let fileList = document.getElementById('file-list');
    let html = '';
    for ( const [key, value] of Object.entries(response.data) ) {
        html += '<tr>';
        html += '<td>' + key + '</td>';
        html += '<td><a href="download/' + key + '">' + value.url + '</a></td>';
        html += '<td class="uk-width-small">' + value.size + '</td>';
        html += '<td class="uk-width-small"><button class="uk-button uk-button-default"><div uk-form-custom><input type="file"><span>UPDATE</span></div></button></td>';
        html += '<td class="uk-width-small"><button class="uk-button uk-button-danger" onclick="deleteFile(\'' + key + '\')">Delete</button></td>';
        html += '</tr>';
    }
    fileList.innerHTML = html;
}

async function deleteFile(file) {
    let response = await fetch('delete/' + file, {
        method: 'DELETE'
    });
    response = await response.json();
    if ( response.ok ) {
        await updateFileList();
        UIkit.notification({message: 'File Deleted', status: 'success'})
    } else {
        UIkit.notification({message: 'File Delete Failed: ' + response.error, status: 'danger'})
    }
}

async function updateFile(file) {
}

async function checkAuth() {
    // check auth using head method
    let response = await fetch('auth', {
        method: 'HEAD'
    });
    if ( response.status === 200 ) {
        // auth ok
        document.getElementById('token').setAttribute('hidden', 'hidden');
        UIkit.notification({message: 'Authenticated', status: 'success'})
    } else {
        // auth failed
        document.getElementById('token').removeAttribute('hidden');
        UIkit.notification({message: 'Not Authenticated', status: 'info'})
    }
}

checkAuth();
// updateFileList();