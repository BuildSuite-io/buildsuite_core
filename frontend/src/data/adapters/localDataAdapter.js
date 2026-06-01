export function createLocalDataAdapter(store) {
  return {
    getRootProjects() {
      return store.rootProjects
    },
    getCompanies() {
      return store.companies
    },
    isMultiCompany() {
      return store.isMultiCompany
    },
    getCompanyById(id) {
      return store.companyById(id)
    },
  }
}
