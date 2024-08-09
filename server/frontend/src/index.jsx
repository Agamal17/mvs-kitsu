import axios from 'axios'
import addonData from '/src/common'
import React, { useContext, useEffect, useState } from 'react'
import ReactDOM from 'react-dom/client'
import { AddonProvider, AddonContext } from '@ynput/ayon-react-addon-provider'

import PairingList from './PairingList'

import '@ynput/ayon-react-components/dist/style.css'

import styled from 'styled-components'
import {ToastContainer} from "react-toastify";
import 'react-toastify/dist/ReactToastify.css'


const MainContainer = styled.div`
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;

  h1 {
    font-size: 18px;
    padding: 0 0 10px 0;
    border-bottom: 1px solid #ccc;
  }
`



const App = () => {
  const accessToken = useContext(AddonContext).accessToken
  const addonName = useContext(AddonContext).addonName
  const addonVersion = useContext(AddonContext).addonVersion
  const [tokenSet, setTokenSet] = useState(false)

  useEffect(() =>{
    if (addonName && addonVersion){
      addonData.addonName = addonName
      addonData.addonVersion = addonVersion
      addonData.baseUrl = `${window.location.origin}/api/addons/${addonName}/${addonVersion}`
    }
      
  }, [addonName, addonVersion])


  useEffect(() => {
    if (accessToken && !tokenSet) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${accessToken}`
      setTokenSet(true)
    }
  }, [accessToken, tokenSet])

  if (!tokenSet) {
    return "no token"
  }

  if (addonName === "test") {
    window.location.reload()
    return
  }

  return <PairingList />
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <AddonProvider debug>
      <MainContainer>
        <App />
      </MainContainer>
      <ToastContainer/>
    </AddonProvider>
  </React.StrictMode>,
)
