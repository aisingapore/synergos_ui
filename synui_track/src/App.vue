<!-- 
  We bootstrap our Component to Streamlit with our scoped slot in the top-level App.
  This is where scoped slot passes Streamlit ;`args` data from itself to children MyComponent.
  You should not have to edit this, but are free to do so :)
-->
<template>
    <div id="app">
        <WithStreamlitConnection v-slot="{ args }">
            <CommandStation :args="args" />
        </WithStreamlitConnection>
    </div>
</template>

<script>
import CommandStation from "./CommandStation.vue";

// "withStreamlitConnection" is a scoped slot. It bootstraps the
// connection between your component and the Streamlit app, and handles
// passing arguments from Python -> Component.
//
// You don't need to edit withStreamlitConnection (but you're welcome to!).
import WithStreamlitConnection from "./streamlit/WithStreamlitConnection.vue";

export default {
    name: "App",
    components: {
        CommandStation,
        WithStreamlitConnection,
    },
};
</script>

<style>
body {
    margin: 0;
}

#app {
    font-family: Avenir, Helvetica, Arial, sans-serif;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    color: #2c3e50;
}
</style>
