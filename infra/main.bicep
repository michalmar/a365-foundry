@description('Azure region for all resources.')
param location string = resourceGroup().location

@description('Container image for the agent host.')
param containerImage string

@description('Azure AI Foundry project endpoint consumed by the host.')
param projectEndpoint string

@description('Foundry agent name to resolve at startup.')
param foundryAgent string = 'OperationsEngineering'

@description('Container Apps environment name.')
param containerAppsEnvironmentName string = 'cae-a365-foundry'

@description('Agent host container app name.')
param containerAppName string = 'ca-a365-foundry-agent'

@description('Azure Bot Service resource name.')
param botName string = 'bot-a365-foundry-agent'

module identity 'identity.bicep' = {
  name: 'identity'
  params: {
    location: location
  }
}

module containerapp 'containerapp.bicep' = {
  name: 'containerapp'
  params: {
    location: location
    containerAppsEnvironmentName: containerAppsEnvironmentName
    containerAppName: containerAppName
    containerImage: containerImage
    projectEndpoint: projectEndpoint
    foundryAgent: foundryAgent
    identityId: identity.outputs.identityId
  }
}

module bot 'bot.bicep' = {
  name: 'bot'
  params: {
    location: location
    botName: botName
    endpoint: 'https://${containerapp.outputs.fqdn}/api/messages'
    userAssignedIdentityClientId: identity.outputs.clientId
  }
}

output botId string = bot.outputs.botId
output containerAppFqdn string = containerapp.outputs.fqdn
output userAssignedIdentityId string = identity.outputs.identityId
