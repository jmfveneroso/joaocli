import React from 'react';
import ReactDOM from 'react-dom';
import {HashRouter, Route, Switch} from 'react-router-dom';

// Styles
// Import Flag Icons Set
import 'flag-icon-css/css/flag-icon.min.css';
// Import Font Awesome Icons Set
import 'font-awesome/css/font-awesome.min.css';
// Import Simple Line Icons Set
import 'simple-line-icons/css/simple-line-icons.css';
// Import Main styles for this application
import '../scss/style.scss'
// Temp fix for reactstrap
import '../scss/core/_dropdown-menu-right.scss'

// Containers
import main from './main/'
import entry from './entry/'

ReactDOM.render((
  <HashRouter>
    <Switch>
      <Route path="/log-entry/:id" component={entry}/>
      <Route path="/" name="main" component={main}/>
    </Switch>
  </HashRouter>
), document.getElementById('root'));
