param location string

resource identity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: 'id-a365-foundry-agent'
  location: location
}

output identityId string = identity.id
output clientId string = identity.properties.clientId
output principalId string = identity.properties.principalId
