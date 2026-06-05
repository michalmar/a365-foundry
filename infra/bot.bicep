param location string
param botName string
param endpoint string
param userAssignedIdentityClientId string

resource bot 'Microsoft.BotService/botServices@2022-09-15' = {
  name: botName
  location: 'global'
  kind: 'azurebot'
  sku: {
    name: 'F0'
  }
  properties: {
    displayName: 'OperationsEngineering'
    endpoint: endpoint
    msaAppType: 'UserAssignedMSI'
    msaAppId: userAssignedIdentityClientId
    isCmekEnabled: false
    publicNetworkAccess: 'Enabled'
  }
}

resource teamsChannel 'Microsoft.BotService/botServices/channels@2022-09-15' = {
  parent: bot
  name: 'MsTeamsChannel'
  location: 'global'
  properties: {
    channelName: 'MsTeamsChannel'
  }
}

output botId string = userAssignedIdentityClientId
