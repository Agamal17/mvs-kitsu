import axios from 'axios'
import addonData from '/src/common'
import { useState, useEffect } from 'react'
import { Panel, ScrollPanel, Button } from '@ynput/ayon-react-components'
import styled from 'styled-components'
import {toast} from 'react-toastify';
import {BeatLoader} from 'react-spinners'


const PairingListPanel = styled(Panel)`
  min-width: 500px;
  min-height: 300px;
  max-height: 90%;
`

const Warn = styled.span`
  color: red;
  font-weight: bold;
`

const Table = styled.table`
  border-collapse: collapse;
  width: 100%;

  thead {
    border-bottom: 1px solid #ccc;
  }

  th, td {
    padding: 0.5rem;
    height: 48px;
  }

  th {
    font-weight: bold;
    text-align: left;
  }
`


const PairingList = () => {
    const [pairings, setPairings] = useState([])
    const [clicked, setClicked] = useState(-1)
    const [projects, setProjects] = useState([])

  const sync = (project_name, idx) => {
        setClicked(idx)
    const entity = idx === -2 ? 'Persons' :'Project'
    toast.loading(`Syncing ${entity}`)
    console.log(`project ${projects[idx]}`)
    axios.post(`${addonData.baseUrl}/sync`, {project: projects[idx], project_name: project_name}).then(
      (res) => {
          toast.dismiss()
          toast.success(`${entity} Synced`)
          setClicked(-1)
      }).catch( (e) => {
        toast.dismiss()
        toast.error(`${entity} Sync Failed`)
        setClicked(-1)
      })
    }

  const loadPairings = () => {
    axios
      .get(`${addonData.baseUrl}/fetch`)
      .then((response) => {
        const project_names = []
          const tmp_projects = []
            for (let i = 0; i < response.data.length; i++) { // @ts-ignore
                tmp_projects.push(response.data[i])
                // @ts-ignore
                project_names.push(response.data[i]["name"])
            }
            setPairings(project_names)
          setProjects(tmp_projects)
        })
      .catch((error) => {

      })
  }

  useEffect(() => {
    loadPairings()
    //   setPairings(["1", "2", "3", "4", "5"])
    //   setProjects(["a", "b", "c"])
    //   setProjects([...projects, "d", "e"])
  }, [])


  return (
    <PairingListPanel>
      <ScrollPanel style={{flexGrow: 1}}>
        <Table>
          <thead>
            <tr>
              <th>Kitsu project name</th>
              <th>{clicked === -2? <BeatLoader style={ {marginLeft : '20px'} } color={"#00dca3"}/>:<Button disabled={clicked !== -1 && clicked !== -2} key = {-2} onClick={ () => sync("", -2)}>Sync Persons</Button>}</th>
              <th style={{width:1}}></th>
            </tr>
          </thead>
          <tbody>
        {pairings.map((pairing, idx) => (
          <tr>
            <td>{pairing}</td>
              <td> {clicked === idx? <BeatLoader style={ {marginLeft : '20px'} } color={"#00dca3"}/>:<Button disabled={clicked !== -1 && clicked !== idx} key = {idx} onClick={ () => sync(pairing, idx)}> Sync Now </Button> }</td>
          </tr>
        ))}
          </tbody>
        </Table>
      </ScrollPanel>
    </PairingListPanel>
  )
}

export default PairingList
