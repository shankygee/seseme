import React from 'react';
import ControlPanel from './components/ControlPanel';
import Settings from './components/Settings';

const App: React.FC = () => {
  return (
    <>
      <ControlPanel />
      <Settings />
    </>
  );
};

export default App;
