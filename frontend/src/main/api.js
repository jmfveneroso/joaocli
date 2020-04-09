import jQuery from 'jquery';

function getCookie() {
  let name = 'csrftoken'
  var cookieValue = null
  if (document.cookie && document.cookie !== '') {
    var cookies = document.cookie.split(';')
    for (var i = 0; i < cookies.length; i++) {
      var cookie = jQuery.trim(cookies[i])
      if (cookie.substring(0, name.length + 1) === (name + '=')) {
        cookieValue = decodeURIComponent(cookie.substring(name.length + 1))
        break
      }
    }
  }
  return cookieValue;
}

class API {
  static request(url, method, body) {
    return fetch(url, {
      method: method,
      mode: 'same-origin',
      // credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        // 'X-CSRFToken': getCookie(),
      },
      body: JSON.stringify(body)
    }).then(function(response) {
      return response.json();
    })
  }

  static createEntry(id, title) {
    return API.request('/entries/', 'post', {
      parent_id: id,
      title: title,
    })
  }

  static updateEntryContent(id, title, content) {
    return API.request('/entries/', 'patch', {
      id: id,
      title: title,
      content: content,
    })
  }

  static updateEntryTag(id, tag_name) {
    return API.request('/entries/', 'patch', {
      id: id,
      tag: tag_name,
    })
  }

  static deleteEntry(id) {
    return API.request('/entries/', 'delete', { id: id })
  }

  static createTag(name, parent_id) {
    return API.request('/tags/', 'post', {
      name: name,  
      parent: parent_id, 
    })
  }

  static editTag(id, name, parent_id) {
    return API.request('/tags/', 'patch', {
      id: id,
      name: name,
      parent: parent_id,
    })
  }

  static deleteTag(id) {
    return API.request('/tags/', 'delete', {
      id: id
    })
  }

  static getAll() {
    return fetch('/all/', {
      method: 'get',
      mode: 'same-origin',
      credentials: 'include',
      headers: {
        'Accept': 'application/json',
        'Content-Type': 'application/json',
        'X-CSRFToken': getCookie(),
      }
    }).then(function(response) {
      return response.json();
    })
  }
}

export default API;
